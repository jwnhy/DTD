import gdb
import os
import re
import random


def format_ptr(val):
    ptrto = None
    value = None
    # special judge c_str
    if str(val.type).endswith('char *'):
        return format_str(val)
    try:
        value = int(val.format_string(raw=True).split()[0], base=16)
    except Exception as e:
        print(e)
        pass
    if value == 0: 
        return {'t': str(val.type), 'v': value, 'ptrto': ptrto}
    try:
        ptrto = format_value(val.dereference())
    except Exception as e:
        print(e)
        pass
    if ptrto is not None and ptrto['v'] is None:
        ptrto = None
    return {'t': str(val.type), 'v': value, 'ptrto': ptrto}

def format_str(val):
    value = None
    try:
        value = val.string()
    except:
        pass
    return {'t': str(val.type), 'v': value}

def format_array(val):
    val_array = []
    nr = val.type.range()[1]+1
    for idx in range(nr):
        val_array.append(format_value(val[idx]))
    return {'t': str(val.type), 'v': val_array}

def format_comp(val):
    member = {}
    for field in val.type.fields():
        member[field.name] = format_value(val[field.name])
    return {'t': str(val.type).replace('struct ', '').replace('enum ', '').replace('union ', ''), 'v': member}

def format_enum(val):
    return {'t': str(val.type), 'v': val.format_string(raw=True)}

def format_int(val):
    value = None
    try:
        value = int(val.format_string(raw=True).split()[0])
    except:
        pass
    if 'char' in str(val.type):
        return format_char(val)
    return {'t': str(val.type), 'v': value}

def format_float(val):
    return {'t': str(val.type), 'v': f'{float(val.format_string(raw=True)):.3f}'}

def format_char(val):
    return {'t': str(val.type), 'v': int(val.format_string(raw=True).split(' ')[0])}

def format_bool(val):
    return {'t': 'bool', 'v': val.format_string(raw=True)}

def format_value(val):
    format_tlb = {
            gdb.TYPE_CODE_PTR: format_ptr,
            gdb.TYPE_CODE_ARRAY: format_array,
            gdb.TYPE_CODE_STRUCT: format_comp,
            gdb.TYPE_CODE_UNION: format_comp,
            gdb.TYPE_CODE_ENUM: format_enum,
            gdb.TYPE_CODE_INT: format_int,
            gdb.TYPE_CODE_FLT: format_float,
            gdb.TYPE_CODE_CHAR: format_char,
            gdb.TYPE_CODE_BOOL: format_bool,
            }
    if val.is_optimized_out:
        if val.type.strip_typedefs().code == gdb.TYPE_CODE_PTR:
            return {'t': str(val.type), 'v': None, 'ptrto': None}
        return {'t': str(val.type), 'v': None}
    return format_tlb[val.type.strip_typedefs().code](val)

# use `dict` to allow variable shadowing
def gen_varset(frame):
    global_varset = {}
    static_varset = {}
    local_varset = {}
    blk = frame.block()
    while blk:
        global_block = blk.global_block if blk.global_block else []
        for sym in global_block:
            if sym.is_variable:
                global_varset[sym.name] = sym
        static_block = blk.static_block if blk.static_block else []
        for sym in static_block:
            if (sym.is_argument or sym.is_variable) and static_varset.get(sym.name) is None:
                static_varset[sym.name] = sym
        if blk.is_global:
            break
        for sym in blk:
            if (sym.is_argument or sym.is_variable) and local_varset.get(sym.name) is None and static_varset.get(sym.name) is None:
                local_varset[sym.name] = sym
        blk = blk.superblock
    return (global_varset, static_varset, local_varset)

def format_var(frame):
    blk = frame.block()
    gv_dict, sv_dict, lv_dict = {}, {}, {}
    gv, sv, lv = gen_varset(frame)
    for vs, vs_dict in [(gv, gv_dict), (sv, sv_dict), (lv, lv_dict)]:
        for sym in vs.values():
            try:
                vs_dict[sym.name] = format_value(sym.value(frame))
            except:
                if sym.type.strip_typedefs().code == gdb.TYPE_CODE_PTR:
                    vs_dict[sym.name] = {'t': str(sym.type), 'v': None, 'ptrto': None}
                vs_dict[sym.name] = {'t': str(sym.type), 'v': None} 

    return gv_dict, sv_dict, lv_dict

def format_frame(frame):
    frame_info = format_line(frame)
    gv, sv, lv = format_var(frame)
    frame_info['gv'] = gv
    frame_info['sv'] = sv
    frame_info['lv'] = lv
    return frame_info

def format_line(frame):
    sal = frame.find_sal()
    pc = frame.pc()
    line = sal.line
    func = str(frame.function())
    #return {'pc': pc}
    return {'pc': pc, 'line': line, 'func': func}

def line_functor(state, res_list):
    cur = format_line(gdb.newest_frame())
    res_list.append(cur)
    if state is None:
        return {}, res_list
    else:
        return state, res_list

def naive_diff_functor(state, res_list):
    cur = format_frame(gdb.newest_frame())
    if state is None:
        res_list.append(cur)
        return {'last': cur}, res_list
    else:
        last = state['last']
        res_list.append(frame_diff(last, cur))
        state['last'] = cur
        return state, res_list

def adaptive_diff_functor(state, res_list):
    # we only format cheap line
    cur = format_line(gdb.newest_frame()) 
    if state is None:
        cur = format_frame(gdb.newest_frame())
        res_list.append((cur, (cur['pc'], True)))
        return {'last': cur, 'seen': {}}, res_list
    else:
        seen = state['seen']
        pc_jmp = (res_list[-1][0]['pc'], cur['pc'])
        gen_full = (pc_jmp not in seen) or random.random() < (1 / seen[pc_jmp])
        seen[pc_jmp] = seen.get(pc_jmp, 0) + 1
        if gen_full:
            # slow here
            cur = format_frame(gdb.newest_frame())
            last = state['last']
            res_list.append((frame_diff(last,cur), (cur['pc'], True)))
            state['last'] = cur

            #new = frame_update(last, frame_diff(last, cur))
            #print(frame_diff(cur, new))
        else:
            res_list.append((cur, (cur['pc'], False)))
        return state, res_list

def trace_diff_functor(state, res_list):
    if state['cnt'] >= len(state['pc_trace']):
        return state, res_list
    base = state['base']
    curbase = state['curbase']
    # expect state['pc_trace'] not None
    pc_trace = state['pc_trace']
    cur = format_line(gdb.newest_frame())
    # if miss-aligned
    if cur['pc']-curbase > pc_trace[state['cnt']][0]-base:
        while cur['pc']-curbase > pc_trace[state['cnt']][0]-base:
            state['cnt'] += 1
        if cur['pc']-curbase != pc_trace[state['cnt']][0]-base:
            print(str(res_list))
            print("Fatal Misalignment!")
            os._exit(0)
    elif cur['pc']-curbase < pc_trace[state['cnt']][0]-base:
        res_list.append(cur)
        return state, res_list

    if len(res_list) == 0:
        cur = format_frame(gdb.newest_frame())
        res_list.append(cur)
        state['last'] = cur
        state['cnt'] += 1
        return state, res_list
    elif pc_trace[state['cnt']][1]:
        cur = format_frame(gdb.newest_frame())
        last = state['last']
        res_list.append(frame_diff(last, cur))
        state['last'] = cur
        state['cnt'] += 1
        return state, res_list
    else:
        res_list.append(cur)
        state['cnt'] += 1
        return state, res_list

def iterate_trace(functor, trace):
    res_list = []
    thread = gdb.selected_thread()
    state = {'cnt': 0, 'pc_trace': trace, 'base': trace[0][0], 'curbase': gdb.newest_frame().pc()}
    state, res_list = functor(state, res_list)
    while thread.is_valid():
        gdb.execute('stepi')
        if not gdb.newest_frame().function():
            gdb.execute('finish')
        if not thread.is_valid():
            break
        state, res_list = functor(state, res_list)
    return res_list


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

        tracefile = open(f'example.step', 'r')
        trace = eval(tracefile.read())

        frame_list = iterate_trace(trace_diff_functor, trace)
        with open("example.gdb", 'w') as trace:
            for f in frame_list:
                trace.write(str(f) + '\n')
        gdb.execute('exit')
    except Exception as e:
        import traceback
        traceback.print_exception(e)
        os._exit(1)
