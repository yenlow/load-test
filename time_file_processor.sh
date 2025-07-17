#!/bin/bash

# Wrapper script to time the execution of file_processor.py for specified number of runs

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
# Check if TOTAL_RUNS is provided as command line argument
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Please provide the number of runs as the first argument${NC}"
    echo -e "Usage: $0 <number_of_runs>"
    echo -e "Example: $0 100"
    exit 1
fi

TOTAL_RUNS=$1
CMD="./venv/bin/python file_processor.py -i docs -n 6"
TIMING_FILE="timing_results.txt"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}TIMING FILE_PROCESSOR.PY - $TOTAL_RUNS RUNS${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Command: ${YELLOW}$CMD${NC}"
echo -e "Total runs: ${YELLOW}$TOTAL_RUNS${NC}"
echo -e "Start time: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"

# Initialize arrays and counters
declare -a TIMES
SUCCESSFUL_RUNS=0
FAILED_RUNS=0

# Clear timing file
> "$TIMING_FILE"

# Run the command multiple times
for ((i=1; i<=TOTAL_RUNS; i++)); do
    echo -e "${CYAN}Run $i/$TOTAL_RUNS${NC}"
    
    # Record start time
    START_TIME=$(date +%s.%N)
    
    # Run the command and capture exit code
    eval $CMD > /dev/null 2>&1
    EXIT_CODE=$?
    
    # Record end time
    END_TIME=$(date +%s.%N)
    
    # Calculate execution time in seconds
    EXECUTION_TIME=$(echo "$END_TIME - $START_TIME" | bc -l)
    
    # Store timing result
    TIMES+=($EXECUTION_TIME)
    
    # Write to timing file
    echo "$EXECUTION_TIME" >> "$TIMING_FILE"
    
    if [ $EXIT_CODE -eq 0 ]; then
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
        echo -e "  ${GREEN}✓ Success${NC} - ${EXECUTION_TIME}s"
    else
        FAILED_RUNS=$((FAILED_RUNS + 1))
        echo -e "  ${RED}✗ Failed${NC} - ${EXECUTION_TIME}s"
    fi
done

echo -e "${BLUE}------------------------------------------------------------${NC}"
echo -e "End time: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"

# Calculate statistics using Python for better precision
STATS=$(python3 -c "
import sys
import statistics

# Read timing data
with open('$TIMING_FILE', 'r') as f:
    times = [float(line.strip()) for line in f if line.strip()]

if times:
    times.sort()
    min_time = min(times)
    max_time = max(times)
    avg_time = statistics.mean(times)
    median_time = statistics.median(times)
    
    # Calculate standard deviation
    if len(times) > 1:
        std_dev = statistics.stdev(times)
    else:
        std_dev = 0
    
    # Calculate percentiles
    p25 = times[int(len(times) * 0.25)]
    p75 = times[int(len(times) * 0.75)]
    p95 = times[int(len(times) * 0.95)]
    
    print(f'{min_time:.3f}')
    print(f'{max_time:.3f}')
    print(f'{avg_time:.3f}')
    print(f'{median_time:.3f}')
    print(f'{std_dev:.3f}')
    print(f'{p25:.3f}')
    print(f'{p75:.3f}')
    print(f'{p95:.3f}')
else:
    print('0.000')
    print('0.000')
    print('0.000')
    print('0.000')
    print('0.000')
    print('0.000')
    print('0.000')
    print('0.000')
")

# Parse statistics
STAT_ARRAY=($(echo "$STATS"))
MIN_TIME=${STAT_ARRAY[0]}
MAX_TIME=${STAT_ARRAY[1]}
AVG_TIME=${STAT_ARRAY[2]}
MEDIAN_TIME=${STAT_ARRAY[3]}
STD_DEV=${STAT_ARRAY[4]}
P25=${STAT_ARRAY[5]}
P75=${STAT_ARRAY[6]}
P95=${STAT_ARRAY[7]}

# Display results
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}TIMING STATISTICS ($TOTAL_RUNS RUNS)${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}Successful runs: $SUCCESSFUL_RUNS${NC}"
echo -e "${RED}Failed runs: $FAILED_RUNS${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"
echo -e "${YELLOW}Timing Statistics (seconds):${NC}"
echo -e "  Minimum:     ${CYAN}${MIN_TIME}s${NC}"
echo -e "  Maximum:     ${CYAN}${MAX_TIME}s${NC}"
echo -e "  Average:     ${CYAN}${AVG_TIME}s${NC}"
echo -e "  Median:      ${CYAN}${MEDIAN_TIME}s${NC}"
echo -e "  Std Dev:     ${CYAN}${STD_DEV}s${NC}"
echo -e "  25th %ile:   ${CYAN}${P25}s${NC}"
echo -e "  75th %ile:   ${CYAN}${P75}s${NC}"
echo -e "  95th %ile:   ${CYAN}${P95}s${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Detailed timing data saved to: ${YELLOW}$TIMING_FILE${NC}" 