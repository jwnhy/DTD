#!/usr/bin/python3
import os
import sys
import pdb
from trace_diff import frame_compare, frame_update

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python comparator.py <trace-1> <trace-2>')
        exit(0)
    trace1 = open(sys.argv[1], 'r').read().splitlines()
    trace2 = open(sys.argv[2], 'r').read().splitlines()
    if len(trace1) == 0 or len(trace2) == 0:
        exit(1)
    # init
    frame1 = eval(trace1[0])
    frame2 = eval(trace2[0])

    base1 = frame1['pc']
    base2 = frame2['pc']

    cnt1 = cnt2 = 1
    seen_diff = set()
    res_dict = {}
    updated = True
    while cnt1 < len(trace1) and cnt2 < len(trace2):
        #print((cnt1, len(trace1)))
        # alignment
        if frame1['pc']-base1 < frame2['pc']-base2:
            while frame1['pc']-base1 < frame2['pc']-base2 and cnt1 < len(trace1):
                frame1, _ = frame_update(frame1, eval(trace1[cnt1]))
                updated = True
                #print(f'{cnt1} {cnt2}: miss frame on right')
                cnt1 += 1
            if frame1['pc']-base1 != frame2['pc']-base2:
                print(f'{sys.argv[1]} {cnt1} {cnt2}: unrecoverable frame', file=sys.stderr)
                exit(1)
        if frame1['pc']-base1 > frame2['pc']-base2:
            while frame1['pc']-base1 > frame2['pc']-base2 and cnt2 < len(trace2):
                frame2, _ = frame_update(frame2, eval(trace2[cnt2]))
                updated = True
                #print(f'{cnt1} {cnt2}: miss frame on left')
                cnt2 += 1
            if frame1['pc']-base1 != frame2['pc']-base2:
                print(f'{sys.argv[1]} {cnt1} {cnt2}: unrecoverable frame', file=sys.stderr)
                exit(1)
        # increment
        if updated:
            diff = frame_compare(frame1, frame2)
        frame1, f1_updated = frame_update(frame1, eval(trace1[cnt1]))
        frame2, f2_updated = frame_update(frame2, eval(trace2[cnt2]))
        updated = f1_updated or f2_updated
        cnt1 += 1
        cnt2 += 1
        if len(diff) != 0:
            for varkey in ['lv', 'sv', 'gv']:
                if varkey not in diff:
                    continue
                for entry in diff[varkey].items():
                    if str(entry) not in seen_diff:
                        seen_diff.add(str(entry))
                    else:
                        continue
                    res_dict[(cnt1, cnt2)] = res_dict.get((cnt1, cnt2), {})
                    res_dict[(cnt1, cnt2)][entry[0]] = (frame1['line'], frame2['line'], frame1['func'], frame2['func'], entry[1])
            for basekey in ['line', 'func']:
                if basekey not in diff:
                    continue
                res_dict[(cnt1, cnt2)] = res_dict.get((cnt1, cnt2), {})
                res_dict[(cnt1, cnt2)][basekey] = diff[basekey]
    for (k, v) in res_dict.items():
        for (var, info) in v.items():
            print(f"On line {info[0]}", end=': ')
            print(f"GDB: {var} = {info[4][0]['v']}", end=', ')
            print(f"LLDB: {var} = {info[4][1]['v']}")
