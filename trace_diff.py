def value_diff(a, b):
    # if `type` is different, directly return
    if a is None and b is None:
        return None
    if a['t'] != b['t']:
        return (b, 'f')
    va = a['v']
    vb = b['v']
    # optimized
    if vb is None:
        return (b, 'f')
    # pointer
    if 'ptrto' in a:
        if va != vb:
            return (b, 'f')
        elif a['ptrto'] is None and b['ptrto'] is None:
            return None
        elif a['ptrto'] is None:
            return ({'ptrto': (b['ptrto'], 'f')}, 'ptr')
        elif b['ptrto'] is None:
            return ({'ptrto': (None, 'f')}, 'ptr')
        elif diff := value_diff(a['ptrto'], b['ptrto']):
            return ({'ptrto': diff}, 'ptr')
        else:
            return None
    # array
    if isinstance(va, list) and isinstance(vb, list):
        update_dict = {}
        if len(va) != len(vb):
            return (b, 'f')
        for idx in range(len(va)):
            if diff := value_diff(va[idx], vb[idx]):
                update_dict[idx] = diff
        if len(update_dict) > 0:
            return (update_dict, 'p')
        else:
            return None
    # struct
    elif isinstance(va, dict) and isinstance(vb, dict):
        update_dict = {}
        for key in va.keys():
            if diff := value_diff(va[key], vb[key]):
                update_dict[key] = diff
        if len(update_dict) > 0:
            return (update_dict, 'p')
        else:
            return None
    # pure value
    elif va != vb:
        return (b, 'f')
    else:
        return None

def partial_update(a, patch):
    update, mode = patch
    if mode == 'f':
        return update
    if mode == 'ptr':
        a['ptrto'] = partial_update(a['ptrto'], update['ptrto'])
        return a
    if isinstance(a['v'], list):
        for idx in update.keys():
            a['v'][idx] = partial_update(a['v'][idx], update[idx])
        return a
    elif isinstance(a['v'], dict):
        for key in update.keys():
            #print(key, var[key], update[key], partial_update(var[key]['v'], update[key]))
            a['v'][key] = partial_update(a['v'][key], update[key])
        return a

def frame_update(old_frame, patch):
    new_frame = old_frame
    new_frame['pc'] = patch['pc']
    new_frame['func'] = patch['func']
    new_frame['line'] = patch['line']
    updated = False
    for var_key in ['gv', 'sv', 'lv']:
        if var_key not in patch:
            continue
        for (key, val) in patch[var_key].items():
            if len(patch[var_key]) > 0:
                updated = True
            if val is None:
                del new_frame[var_key][key]
                continue
            update, mode = val
            if mode == 'f':
                new_frame[var_key][key] = update
            if mode == 'p':
                #print(key)
                new_frame[var_key][key] = partial_update(new_frame[var_key][key], val)
            if mode == 'ptr':
                new_frame[var_key][key] = partial_update(new_frame[var_key][key], val)
    return new_frame, updated

def frame_diff(old_frame,  new_frame):
    update = { 'pc': new_frame['pc'],'line': new_frame['line'], 'func':new_frame['func'], 'gv': {}, 'sv': {}, 'lv': {}}
    #update = { 'pc': new_frame['pc'], 'gv': {}, 'sv': {}, 'lv': {}}
    for var_key in ['gv', 'sv', 'lv']:
        oldvkey = set(old_frame[var_key].keys())
        newvkey = set(new_frame[var_key].keys())
        # fully update for del/new vars in the new frame
        for del_var in oldvkey.difference(newvkey):
            update[var_key][del_var] = None
        for add_var in newvkey.difference(oldvkey):
            update[var_key][add_var] = (new_frame[var_key][add_var], 'f')
        # partial update for common variables
        for common_var in oldvkey.intersection(newvkey):
            #print(common_var)
            if diff := value_diff(old_frame[var_key][common_var], new_frame[var_key][common_var]):
                update[var_key][common_var] = diff
    return update

def standard_type(a):
    a = a.replace(' [', '[')
    if a == 'long':
        a = 'long int'
    return a

def value_compare(a, b):
    # if `type` is different, directly return
    #if standard_type(a['t']) != standard_type(b['t']):
       #return (a, b)
    va = a['v']
    vb = b['v']
    if va is None and vb is not None:
        return (a, b)
    if va is not None and vb is None:
        return (a, b)
    # pointer
    if 'ptrto' in a and 'ptrto' in b:
        if a['ptrto'] is None and b['ptrto'] is None:
            return None
        elif a['ptrto'] is None:
            return ({'ptrto': None}, {'ptrto': b['ptrto']})
        elif b['ptrto'] is None:
            return ({'ptrto': a['ptrto']}, {'ptrto': None})
        elif diff := value_compare(a['ptrto'], b['ptrto']):
            return ({'ptrto': diff[0]}, {'ptrto': diff[1]})
        else:
            return None
    # array
    if isinstance(va, list) and isinstance(vb, list):
        diff_tuple = ({}, {})
        if len(va) != len(vb):
            return (va, vb)
        for idx in range(len(va)):
            if diff := value_compare(va[idx], vb[idx]):
                diff_tuple[0][idx] = diff[0]
                diff_tuple[1][idx] = diff[1]
        if len(diff_tuple[0]) > 0:
            return diff_tuple
        else:
            return None
    # struct
    elif isinstance(va, dict) and isinstance(vb, dict):
        diff_tuple = ({}, {})
        for key in va.keys():
            if diff := value_compare(va[key], vb[key]):
                diff_tuple[0][key] = diff[0]
                diff_tuple[1][key] = diff[1]
        if len(diff_tuple[0]) > 0:
            return diff_tuple
        else:
            return None
    
    # pure value
    elif va != vb:
        return (a, b)
    else:
        return None

def frame_compare(left, right):
    diff = {}
    for base_key in ['pc', 'func', 'line']:
        if right[base_key] != left[base_key]:
            diff[base_key] = (left[base_key], right[base_key])
    for var_key in ['gv', 'sv', 'lv']:
        leftvkey = set(left[var_key].keys())
        rightvkey = set(right[var_key].keys())
        # fully update for del/new vars in the new frame
        for left_var in leftvkey.difference(rightvkey):
            if var_key not in diff:
                diff[var_key] = {}
            diff[var_key][left_var] = (left[var_key][left_var], None)
        for right_var in rightvkey.difference(leftvkey):
            if var_key not in diff:
                diff[var_key] = {}
            diff[var_key][right_var] = (None, right[var_key][right_var])
        # partial update for common variables
        for common_var in leftvkey.intersection(rightvkey):
            if vardiff := value_compare(right[var_key][common_var], left[var_key][common_var]):
                if var_key not in diff:
                    diff[var_key] = {}
                diff[var_key][common_var] = vardiff
    return diff
