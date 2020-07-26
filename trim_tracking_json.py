#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
import json, jsonschema
import numpy as np
from scipy.ndimage import zoom
#sys.path.append(os.path.join(thispath,'..'))

parser = argparse.ArgumentParser()
parser.add_argument('trackfile', type=str)
parser.add_argument('-ss', '--trimstart',    type=float, required=True)
parser.add_argument('-te', '--trimend',      type=float, default=-1.)
parser.add_argument('-td', '--trimduration', type=float, default=-1.)
parser.add_argument('-o', '--outfile',       type=str, default='')
args = parser.parse_args()

if args.trimend < 0. and args.trimduration < 0.:
    args.trimend      = int(1e9)
    args.trimduration = int(1e9)
else:
    assert not (args.trimend > 0. and args.trimduration > 0.), 'use one or the other'
    if args.trimduration > 0.:
        args.trimend = args.trimstart + args.trimduration
    else:
        args.trimduration = args.trimend - args.trimstart
        assert args.trimduration > 0., str(args.trimend)+', '+str(args.trimstart)

assert os.path.isfile(args.trackfile), args.trackfile
assert args.trackfile.endswith('.json'), args.trackfile
with open(args.trackfile,'r') as infile:
    trdat = json.load(infile)

#{"tracking": [...],
# "meta": {"sampling_rate": 1, "video_duration": 3963.473, "num_frames": 3967, "width": 3840, "sample_fps": 30, "video_fps": 30.041}}

def idx2time(idx_):
    return float(idx_ )*float(trdat['meta']['video_fps'])/float(trdat['meta']['sample_fps'])
def time2idx(time_):
    return float(time_)*float(trdat['meta']['sample_fps'])/float(trdat['meta']['video_fps'])

tschema = {"type":"object", "properties": { \
        "tracking": {"type":"array", "items":{"type":"number"}},
        "meta": {
                "sampling_rate":  "integer",
                "video_duration": "number",
                "num_frames": "integer",
                "width": "integer",
                "sample_fps": "number",
                "video_fps": "number"
                }
    }}

jsonschema.validate(trdat, tschema)

def dozom(arr,zfact):
    return zoom(arr, zfact, order=0, mode='nearest', prefilter=False)

ZOOMFACT = 100.
newdat = dozom(np.float32(trdat['tracking']), ZOOMFACT)

#trimstart = int(round(  (args.trimstart / float(trdat['meta']['video_duration'])) * float(newdat.shape[0])  ))
#trimend   = int(round(  (args.trimend   / float(trdat['meta']['video_duration'])) * float(newdat.shape[0])  ))
trimstart = int(round(  time2idx(args.trimstart*ZOOMFACT)  ))
trimend   = int(round(  time2idx(args.trimend *ZOOMFACT)   ))

#print("newdat.shape "+str(newdat.shape))
print("trimsta "+str(trimstart))
print("trimend "+str(trimend))

newdat = newdat[trimstart:trimend:int(round(ZOOMFACT))]
#newdat = dozom(newdat[trimstart:trimend], 1.0/ZOOMFACT)
newdat = list([int(round(float(vv))) for vv in newdat.tolist()])

#print("ogdat :\n"+str(trdat['tracking'][:30]))
#print("newdat:\n"+str(newdat))

if args.trimduration > 1e8:
    args.trimduration = idx2time(len(newdat))

trdat['tracking'] = newdat
trdat['meta']['video_duration'] = args.trimduration
trdat['meta']['num_frames'] = len(newdat)

if len(args.outfile) <= 1:
    args.outfile = args.trackfile[:-len('.json')]+'_trimmed.json'
with open(args.outfile,'w') as outfile:
    json.dump(trdat, outfile)
