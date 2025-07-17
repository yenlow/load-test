#!/usr/bin/env python3
"""
PDF to Markdown Converter using pymupdf4llm
Converts PDF files from the docs folder to markdown format for use with Claude.
"""

import os
import glob
import argparse
import random
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pymupdf4llm import to_markdown


class PDFProcessor:
    """Handles PDF processing and conversion to markdown."""

    def __init__(self, input_folder: str, output_folder: str = "markdown_output"):
        """
        Initialize the PDF processor.

        Args:
            input_folder: Path to the folder containing PDF files
            output_folder: Path to the folder where markdown files will be saved
        """
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)

    def get_pdf_files(self) -> List[Path]:
        """Get all PDF files from the docs folder."""
        pdf_pattern = self.input_folder / "*.pdf"
        return list(Path(self.input_folder).glob("*.pdf"))

    def convert_pdf_to_markdown(self, pdf_path: Path) -> Optional[str]:
        """
        Convert a single PDF file to markdown.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Markdown content as string, or None if conversion fails
        """
        try:
            print(f"Converting: {pdf_path.name}")

            # Convert PDF to markdown using pymupdf4llm
            markdown_content = to_markdown(
                str(pdf_path),
                pages=None,  # Convert all pages
                page_chunks=False,
                ignore_images=True,
                table_strategy=None,
            )
            return markdown_content

        except Exception as e:
            print(f"Error converting {pdf_path.name}: {str(e)}")
            return None

    def save_markdown(self, filename: str, content: str) -> Path:
        """
        Save markdown content to a file.

        Args:
            filename: Name of the file (without extension)
            content: Markdown content

        Returns:
            Path to the saved file
        """
        # Clean filename for markdown
        clean_filename = filename.replace(" ", "_").replace(".pdf", "")
        output_path = self.output_folder / f"{clean_filename}.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    def create_index_file(self, processed_files: List[Dict]) -> Path:
        """
        Create an index file with information about all processed files.

        Args:
            processed_files: List of dictionaries with file information

        Returns:
            Path to the index file
        """
        index_path = self.output_folder / "index.md"

        index_content = f"""# PDF Documents Index

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Processed Documents

"""

        for file_info in processed_files:
            index_content += f"""### {file_info['original_name']}

- **Original PDF**: `{file_info['pdf_path']}`
- **Markdown File**: `{file_info['markdown_path']}`
- **Status**: {file_info['status']}
- **Size**: {file_info['size']} bytes

"""

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

        return index_path

    def create_combined_markdown(self, processed_files: List[Dict]) -> Path:
        """
        Create a combined markdown file with all documents.

        Args:
            processed_files: List of dictionaries with file information

        Returns:
            Path to the combined file
        """
        combined_path = self.output_folder / "all_documents.md"

        combined_content = ""

        for file_info in processed_files:
            if file_info["status"] == "success":
                try:
                    with open(file_info["markdown_path"], "r", encoding="utf-8") as f:
                        doc_content = f.read()
                    combined_content += f"""## {file_info['original_name']}

{doc_content}

---
"""
                except Exception as e:
                    print(f"Error reading {file_info['markdown_path']}: {str(e)}")

        with open(combined_path, "w", encoding="utf-8") as f:
            f.write(combined_content)

        return combined_path

    def create_features_json(self, processed_files: List[Dict]) -> Path:
        """
        Create a features.json file with LLM messages format containing markdown content.

        Args:
            processed_files: List of dictionaries with file information

        Returns:
            Path to the features.json file
        """
        features_path = self.output_folder / "features.json"

        # Read the combined markdown content
        combined_path = self.output_folder / "all_documents.md"
        try:
            with open(combined_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
        except Exception as e:
            print(f"Error reading combined markdown file: {str(e)}")
            markdown_content = ""

        # Escape backslashes in the markdown content
        escaped_markdown = markdown_content.replace("\\", "\\\\")

        # Create the messages structure
        messages = [
            {
                "role": "assistant",
                "content": "You are a helpful assistant that can answer questions about IT support based on the documents provided in markdown.",
            },
            {
                "role": "user",
                "content": f"How do I clear paper jams in the copier?\n\nSupporting documents in markdown:\n\n{escaped_markdown}",
            },
        ]

        # Create the features.json structure
        features_data = {"messages": messages}

        # Write to JSON file
        with open(features_path, "w", encoding="utf-8") as f:
            json.dump(features_data, f, indent=2, ensure_ascii=False)

        return features_path

    def process_single_pdf(self, pdf_path: Path) -> Dict:
        """
        Process a single PDF file and return file info.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with file processing information
        """
        file_info = {
            "original_name": pdf_path.name,
            "pdf_path": str(pdf_path),
            "size": pdf_path.stat().st_size,
            "status": "pending",
        }

        try:
            # Convert PDF to markdown
            markdown_content = self.convert_pdf_to_markdown(pdf_path)

            if markdown_content:
                # Save markdown file
                markdown_path = self.save_markdown(pdf_path.stem, markdown_content)
                file_info["markdown_path"] = str(markdown_path)
                file_info["status"] = "success"
                print(f"✓ Successfully converted: {pdf_path.name}")
            else:
                file_info["status"] = "failed"
                file_info["markdown_path"] = None
                print(f"✗ Failed to convert: {pdf_path.name}")

        except Exception as e:
            file_info["status"] = "failed"
            file_info["markdown_path"] = None
            file_info["error"] = str(e)
            print(f"✗ Error processing {pdf_path.name}: {str(e)}")

        return file_info

    def process_5_pdfs(
        self,
        max_workers: int = None,
    ) -> Dict:
        """
        Process 5 randomly selected PDF files from the input folder using parallel processing.

        Args:
            max_workers: Maximum number of worker threads (default: min(32, os.cpu_count()))

        Returns:
            Dictionary with processing results
        """
        pdf_files = self.get_pdf_files()

        if not pdf_files:
            print(f"No PDF files found in {self.input_folder}")
            return {
                "processed": [],
                "total": 0,
                "success": 0,
                "failed": 0,
            }

        print(f"Found {len(pdf_files)} PDF files in input folder")

        # Randomly select 5 PDFs without replacement
        num_to_select = 5
        selected_pdfs = random.sample(pdf_files, num_to_select)

        print(f"Randomly selected {num_to_select} PDF files for processing:")
        for i, pdf_path in enumerate(selected_pdfs, 1):
            print(f"  {i}. {pdf_path.name}")

        # Set default max_workers if not provided
        if max_workers is None:
            max_workers = min(32, (os.cpu_count() or 1))

        print(f"Processing with {max_workers} worker threads...")

        processed_files = []
        success_count = 0
        failed_count = 0

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit PDF processing tasks for selected files only
            future_to_pdf = {
                executor.submit(self.process_single_pdf, pdf_path): pdf_path
                for pdf_path in selected_pdfs
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_pdf):
                pdf_path = future_to_pdf[future]
                try:
                    file_info = future.result()
                    processed_files.append(file_info)

                    if file_info["status"] == "success":
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    print(f"✗ Unexpected error processing {pdf_path.name}: {str(e)}")
                    failed_count += 1
                    processed_files.append(
                        {
                            "original_name": pdf_path.name,
                            "pdf_path": str(pdf_path),
                            "size": pdf_path.stat().st_size if pdf_path.exists() else 0,
                            "status": "failed",
                            "markdown_path": None,
                            "error": str(e),
                        }
                    )

        # Sort processed files by original name for consistent output
        processed_files.sort(key=lambda x: x["original_name"])

        # Create index and combined files
        if processed_files:
            # index_path = self.create_index_file(processed_files)
            # print(f"\nIndex file created: {index_path}")
            combined_path = self.create_combined_markdown(processed_files)
            features_path = self.create_features_json(processed_files)
            print(f"Combined file created: {combined_path}")
            print(f"Features JSON file created: {features_path}")

        results = {
            "processed": processed_files,
            "total": len(pdf_files),
            "success": success_count,
            "failed": failed_count,
            "output_folder": str(self.output_folder),
            "max_workers": max_workers,
        }
        return results


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert PDF files to markdown format using pymupdf4llm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python file_processor.py --input-folder docs
  python file_processor.py --input-folder ./my_pdfs --output-folder ./my_output
  python file_processor.py --input-folder docs --max-workers 8 
  python file_processor.py --help
        """,
    )

    parser.add_argument(
        "--input-folder",
        "-i",
        type=str,
        required=True,
        help="Path to the folder containing PDF files",
    )

    parser.add_argument(
        "--output-folder",
        "-o",
        type=str,
        default="markdown_output",
        help="Path to the folder where markdown files will be saved (default: markdown_output)",
    )

    parser.add_argument(
        "--max-workers",
        "-n",
        type=int,
        default=1,
        help="Maximum number of worker threads for parallel processing (default: 1)",
    )
    return parser.parse_args()


def main():
    """Main function to run the PDF processor."""
    # Parse command line arguments
    args = parse_arguments()

    print("PDF to Markdown Converter")
    print("=" * 50)

    print(f"Docs folder: {args.input_folder}")
    print(f"Output folder: {args.output_folder}")
    print(f"Max workers: {args.max_workers or 'auto'}")
    print("-" * 50)

    # Initialize processor with command line arguments
    processor = PDFProcessor(
        input_folder=args.input_folder, output_folder=args.output_folder
    )

    # Process 5 randomly selected PDFs
    results = processor.process_5_pdfs(max_workers=args.max_workers)

    # Print summary
    print("\n" + "=" * 50)
    print("PROCESSING SUMMARY")
    print("=" * 50)
    print(f"Total PDFs found: {results['total']}")
    print(f"Successfully converted: {results['success']}")
    print(f"Failed conversions: {results['failed']}")
    print(f"Output folder: {results['output_folder']}")
    print(f"Worker threads used: {results.get('max_workers', 'N/A')}")

    if results["failed"] > 0:
        print("\nFailed conversions:")
        for file_info in results["processed"]:
            if file_info["status"] == "failed":
                error_msg = (
                    f" - {file_info.get('error', 'Unknown error')}"
                    if "error" in file_info
                    else ""
                )
                print(f"  - {file_info['original_name']}{error_msg}")

    # Save results to JSON file (unless disabled)
    results_file = processor.output_folder / "processing_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {results_file}")
    print("\nYou can now use the markdown files with Claude!")


if __name__ == "__main__":
    main()
