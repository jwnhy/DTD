#!/usr/bin/env python
import os
import sys
import lldb
from trace_diff import frame_diff
def format_ptr(val):
    ptrto = None
    value = None
    if str(val.type).endswith('char *'):
        return format_str(val)
    try:
        value = int(val.GetValue(), base=16)
    except:
        pass
    if value == 0: 
        return {'t': val.GetDisplayTypeName(), 'v': value, 'ptrto': ptrto}
    try:
        ptrto = format_value(val.Dereference())
    except:
        pass
    if ptrto is not None and ptrto['v'] is None:
        ptrto = None
    return {'t': val.GetDisplayTypeName(), 'v': value, 'ptrto': ptrto}

def format_str(val):
    value = None
    try:
        val.SetFormat(lldb.eFormatCString)
        value = val.GetValue()
    except:
        pass
    # [1:-1] to remove prefix/suffix quotation
    if value is not None:
        value = value[1:-1]
    return {'t': val.GetDisplayTypeName(), 'v': value}

def format_array(val):
    val_array = []
    nr = val.GetNumChildren()
    for idx in range(nr):
        child = val.GetChildAtIndex(idx)
        val_array.append(format_value(child))
    return {'t': val.GetDisplayTypeName(), 'v': val_array}


def format_comp(val):
    member = {}
    nr = val.GetNumChildren()
    for idx in range(nr):
        child = val.GetChildAtIndex(idx)
        if child.GetName() is None:
            continue
        member[child.GetName()] = format_value(child)
    return {'t': val.GetDisplayTypeName(), 'v': member}

def format_enum(val):
    value = None
    try:
        value = str(val.GetValue())
    except Exception as e:
        pass
    return {'t': str(val.GetDisplayTypeName()), 'v': value}

def format_int(val):
    value = None
    try:
        value = int(val.GetValue())
    except Exception as e:
        pass
    return {'t': val.GetDisplayTypeName(), 'v': value}

def format_uint(val):
    value = None
    try:
        value = int(val.GetValue())
    except Exception as e:
        pass
    return {'t': val.GetDisplayTypeName(), 'v': value}

def format_float(val):
    value = None
    try:
        value = f'{float(val.GetValue()):.3f}'
    except:
        pass
    return {'t': val.GetDisplayTypeName(), 'v': value}

def format_char(val):
    value = None
    err = lldb.SBError()
    try:
        value = int(val.GetValueAsUnsigned(err))
        value = value & 0xff
    except:
        pass
    return {'t': val.GetDisplayTypeName(), 'v': value}

def format_bool(val):
    value = None
    try:
        value = val.GetValue()
    except:
        pass
    return {'t': 'bool','v': value}

def format_basic(val):
    format_tlb = {
            lldb.eBasicTypeBool: format_bool,
            lldb.eBasicTypeInt: format_int,
            lldb.eBasicTypeUnsignedInt: format_uint,
            lldb.eBasicTypeFloat: format_float,
            lldb.eBasicTypeChar: format_char,
            lldb.eBasicTypeSignedChar: format_char,
            lldb.eBasicTypeUnsignedChar: format_char,
            lldb.eBasicTypeLong: format_int,
            lldb.eBasicTypeUnsignedLong: format_uint,
            lldb.eBasicTypeLongLong: format_int,
            lldb.eBasicTypeUnsignedLongLong: format_uint,
            lldb.eBasicTypeShort: format_int,
            lldb.eBasicTypeUnsignedShort: format_uint,
            lldb.eBasicTypeDouble: format_float,
            lldb.eBasicTypeLongDouble: format_float,
            lldb.eBasicTypeShort: format_int,
            lldb.eBasicTypeUnsignedShort: format_uint,
            }
    res = format_tlb[val.GetType().GetCanonicalType().GetBasicType()](val)
    if res is None:
        return {'t': val.GetDisplayTypeName(), 'v': None}
    return res

def format_value(val):
    format_tlb = {
            lldb.eTypeClassPointer: format_ptr, 
            lldb.eTypeClassArray: format_array,
            lldb.eTypeClassStruct: format_comp,
            lldb.eTypeClassUnion: format_comp,
            lldb.eTypeClassEnumeration: format_enum,
            lldb.eTypeClassBuiltin: format_basic,
            }
    res = format_tlb[val.GetType().GetCanonicalType().GetTypeClass()](val)
    if res is None:
        print(val)
        if val.GetType().GetCanonicalType().GetTypeClass() == lldb.eTypeClassPointer:
            return {'t': val.GetDisplayTypeName(), 'v': None, 'ptrto': None}
        return {'t': val.GetDisplayTypeName(), 'v': None}
    return res


def gen_varset(frame, debugger):
    target = debugger.GetSelectedTarget()
    module = target.module[target.executable.basename]
    lv = frame.GetVariables(True, True, False, True)
    gsv = frame.get_statics()
    #gsv = frame.GetVariables(False, False, True, False)
    return gsv, lv
    
def format_var(frame, debugger):
    gsv, lv = gen_varset(frame, debugger)

    gv_dict, sv_dict, lv_dict = {}, {}, {}
    for val in gsv:
        if val.GetValueType() == lldb.eValueTypeVariableGlobal:
            gv_dict[val.GetName()] = format_value(val)
        if val.GetValueType() == lldb.eValueTypeVariableStatic:
            sv_dict[val.GetName()] = format_value(val)
    for val in lv:
        lv_dict[val.GetName()] = format_value(val)
    return gv_dict, sv_dict, lv_dict

def format_frame(frame, debugger):
    frame_info = format_line(frame,debugger)
    gv, sv, lv = format_var(frame, debugger)
    frame_info['gv'] = gv
    frame_info['sv'] = sv
    frame_info['lv'] = lv
    return frame_info

def format_line(frame, debugger):
    #target = debugger.GetSelectedTarget()
    le = frame.GetPCAddress().GetLineEntry()
    pc = frame.GetPC()
    line = le.line
    func = frame.GetFunctionName()
    #return {'pc': pc}
    return {'pc':pc, 'line': line, 'func': func}

def line_functor(thread, debugger, state, res_list):
    cur = format_line(thread.frames[0], debugger)
    res_list.append(cur)
    if state is None:
        return {}, res_list
    else:
        return state, res_list

def naive_diff_functor(thread, debugger, state, res_list):
    cur = format_frame(thread.frames[0], debugger)
    if state is None:
        res_list.append(cur)
        return {'last': cur}, res_list
    else:
        last = state['last']
        res_list.append(frame_diff(last, cur))
        state['last'] = cur
        return state, res_list

def trace_diff_functor(thread, debugger, state, res_list):
    if state['cnt'] >= len(state['pc_trace']):
        return state, res_list
    base = state['base']
    curbase = state['curbase']
    # expect state['pc_trace'] not None
    pc_trace = state['pc_trace']
    cur = format_line(thread.frames[0], debugger)
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
        cur = format_frame(thread.frames[0], debugger)
        res_list.append(cur)
        state['last'] = cur
        state['cnt'] += 1
        return state, res_list
    elif pc_trace[state['cnt']][1]:
        cur = format_frame(thread.frames[0], debugger)
        last = state['last']
        res_list.append(frame_diff(last, cur))
        state['last'] = cur
        state['cnt'] += 1
        return state, res_list
    else:
        res_list.append(cur)
        state['cnt'] += 1
        return state, res_list

def iterate_trace(thread, debugger, trace):
    state = {'cnt': 0, 'pc_trace': trace, 'base': trace[0][0], 'curbase': thread.frames[0].GetPC()}
    res_list = []
    state, res_list = trace_diff_functor(thread, debugger, state, res_list)
    process = thread.GetProcess()
    while process.state != lldb.eStateExited:
        thread.StepInstruction(False)
        frame = thread.frames[0]
        while frame.GetFunctionName() is None or not frame.GetPCAddress().GetLineEntry().IsValid():
            res = lldb.SBCommandReturnObject()
            ce = lldb.SBExecutionContext(thread)
            ci = debugger.GetCommandInterpreter()
            ci.HandleCommand('thread step-out', ce, res)
            frame = thread.frames[0]
            if not res.Succeeded():
                ci.HandleCommand('continue', ce, res)
            if thread.GetProcess().state == lldb.eStateExited:
                return res_list
        state, res_list = trace_diff_functor(thread, debugger, state, res_list)
    return res_list
       
def iterate_frame(thread, debugger, functor):
    state = None
    res_list = []
    state, res_list = functor(thread, debugger, state, res_list)
    process = thread.GetProcess()
    while process.state != lldb.eStateExited:
        thread.StepInstruction(False)
        frame = thread.frames[0]
        while frame.GetFunctionName() is None or not frame.GetPCAddress().GetLineEntry().IsValid():
            res = lldb.SBCommandReturnObject()
            ce = lldb.SBExecutionContext(thread)
            ci = debugger.GetCommandInterpreter()
            ci.HandleCommand('thread step-out', ce, res)
            frame = thread.frames[0]
            if not res.Succeeded():
                ci.HandleCommand('continue', ce, res)
            if thread.GetProcess().state == lldb.eStateExited:
                return res_list
        state, res_list = functor(thread, debugger, state, res_list)
    return res_list

   
def __lldb_init_module(debugger, internal_dict):
    try:
        debugger.SetAsync(False)
        target = debugger.GetSelectedTarget()
        module = target.module[target.executable.basename]
        trace_name = target.executable.basename.split('.')[0]

        res = lldb.SBCommandReturnObject()
        ci = debugger.GetCommandInterpreter()
        ci.HandleCommand('b &main', res)
        ci.HandleCommand('settings set target.disable-aslr false', res)

        #main_bp = target.BreakpointCreateByName('main', target.GetExecutable().GetFilename())
        file = open('example.lldb', 'w')
        tracefile = open(f'example.step', 'r')
        trace = eval(tracefile.read())
   
        process = target.LaunchSimple(None, None, os.getcwd())
        thread = process.GetThreadAtIndex(0)
        frame_list = iterate_trace(thread, debugger, trace)
        for f in frame_list:
            print(str(f), file=file)
        debugger.Terminate()
        file.close()
        os._exit(0)
    except:
        # TODO: add logging
        os._exit(1)
