import gdb
import os
import re
import random


def format_line(frame):
    sal = frame.find_sal()
    pc = frame.pc()
    line = sal.line
    func = str(frame.function())
    #return {'pc': pc}
    return {'pc': pc, 'line': line, 'func': func}

def step_trace_functor(state, res_list):
    # we only format cheap line
    cur = format_line(gdb.newest_frame()) 
    if state is None:
        res_list.append((cur['pc'], True))
        return {'last': cur, 'seen': {}, 'cnt': 1}, res_list
    else:
        seen = state['seen']
        state['cnt'] += 1
        if state['cnt'] > 100 and len(seen) < 5:
            # dead loop detected
            os._exit(2)
        pc_jmp = (res_list[-1][0], cur['pc'])
        gen_full = (pc_jmp not in seen) or random.random() < (1 / (seen[pc_jmp] ** 1.5))
        seen[pc_jmp] = seen.get(pc_jmp, 0) + 1
        res_list.append((cur['pc'], gen_full))
        return state, res_list

def iterate_frame(functor):
    state = None
    res_list = []
    thread = gdb.selected_thread()
    state, res_list = functor(state, res_list)
    while thread.is_valid():
        gdb.execute('stepi')
        if not gdb.newest_frame().function():
            gdb.execute('finish')
        if not thread.is_valid():
            break
        state, res_list = functor(state, res_list)
        if state['cnt'] > 200000:
            os._exit(3)
    return res_list

if __name__ == '__main__':
    try:
        with open('./trace_diff.py') as difffile:
            exec(difffile.read())
        gdb.execute('set disable-randomization off')
        gdb.execute('b *main')
        gdb.execute('r')
        trace_name = os.path.basename(gdb.objfiles()[0].filename).split('.')[0]
        gdb.execute('disable pretty-printer')
        gdb.execute('set style enabled off')
        gdb.execute('set logging enabled off')
        gdb.execute('set logging overwrite on')
        gdb.execute('set logging redirect on')
        gdb.execute('set logging debugredirect off')
        gdb.execute(f'set logging file {trace_name}_debug')
        gdb.execute('set logging enabled off')
        step_trace = iterate_frame(step_trace_functor)
        step_trace = list(step_trace)
        with open(f'example.step', 'w') as trace:
            trace.write(str(step_trace))
        gdb.execute('exit')
    except Exception as e:
        os._exit(1)
