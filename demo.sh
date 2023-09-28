#!/bin/bash

# Compile the binary
gcc example.c -g -o example

# Heuristically generate when collecting full trace when not
gdb -x step_generater.py a.out

# Generate lldb's result
lldb -o "command script import ./lldb_script.py" example

# Generate gdb's result
gdb -x gdb_script.py example

# Compare two trace to obtain the discrepancies
python comparator.py example.gdb example.lldb


