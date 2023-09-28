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

## What does a "debugger trace" look like?
Take the above program for an example. A trace consists of a consecutive program states fetched from the debugger.
Each state provides the following information,
- Program counter: `pc`
- Source code line: `line`
- Function name: `func`
- Variables from different scope: `gv`, `sv`, `lv`

Since we've designed incremental log compression, only changes in these states are logged.
```python
{'pc': 93870933500232, 'line': 10, 'func': 'main', 'gv': {'a': {'t': 'int', 'v': 1}}, 'sv': {}, 'lv': {}}
{'pc': 93870933500233, 'line': 10, 'func': 'main', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500236, 'line': 10, 'func': 'main', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500241, 'line': 10, 'func': 'main', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500197, 'line': 2, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {'i': ({'t': 'int', 'v': 0}, 'f')}}
{'pc': 93870933500198, 'line': 2, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500201, 'line': 4, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500207, 'line': 4, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500211, 'line': 4, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500203, 'line': 4, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500207, 'line': 4, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {'i': ({'t': 'int', 'v': 1}, 'f')}}
{'pc': 93870933500211, 'line': 4, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500213, 'line': 5, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500219, 'line': 5, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500221, 'line': 5, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500223, 'line': 6, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {'b': ({'t': 'short', 'v': 0}, 'f')}}
{'pc': 93870933500229, 'line': 9, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {'b': None}}
{'pc': 93870933500230, 'line': 9, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500231, 'line': 9, 'func': 'func', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500246, 'line': 10, 'func': 'main', 'gv': {}, 'sv': {}, 'lv': {'i': None}}
{'pc': 93870933500251, 'line': 10, 'func': 'main', 'gv': {}, 'sv': {}, 'lv': {}}
{'pc': 93870933500252, 'line': 10, 'func': 'main', 'gv': {}, 'sv': {}, 'lv': {}}
```

## File list

- `comparator.py`: Compare two traces and yield their differences.
- `gdb_script.py`: GDB interpreted python script to generate "debugger trace" of a binary.
- `lldb_script.py`: LLDB interpreted python script to generate "debugger trace" of a binary.
- `step_generator.py`: Heuristically generate which steps to collect *complete* debugger trace.
- `trace_diff.py`: Utility python script for trace diff.


