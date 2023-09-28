# DTD
This is the repository for paper "DTD: Comprehensive and Scalable Testing for Debuggers"

## Bugs we've found
Please go to [our google site](https://sites.google.com/view/dtd-supplementary/#h.i3lgdn47onno) for a complete list of bugs we've found in GDB/LLDB.
## Motivating example
The following is an example C program that triggers a bug in GDB.
This bug occurs when the source is compiled using GCC. We observe this in O1,O2,O3, even O0, hooray), meaning this is a *debugger* bug instead of a compiler bug (which previous works focuses on).
DTD is very good at locating such bugs.

```c
int a = 1;
int func() {
    int i;
    for (; i < 1; i++);
    if (a) {
        short b = 2; /* error point */
        { int i; }
    }
}
int main() { func(); }
```

Just run `demo.sh` to see how DTD detect and report this bug.
```bash
./demo.sh
```
Here is the expected output.
```
On line 6: LLDB: i = 1, GDB: i = opted
```

It says that, on line 6, LLDB saw an variable `i` with value `1`, but GDB saw `i` has been optimized. Therefore, there is a bug in GDB causing `i` gone missing or a bug in LLDB causing a spurious `i` to appear.

## File list

- `comparator.py`: Compare two traces and yield their differences.
- `gdb_script.py`: GDB interpreted python script to generate "debugger trace" of a binary.
- `lldb_script.py`: LLDB interpreted python script to generate "debugger trace" of a binary.
- `step_generator.py`: Heuristically generate which steps to collect *complete* debugger trace.
- `trace_diff.py`: Utility python script for trace diff.


