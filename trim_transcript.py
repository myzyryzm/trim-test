#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
import json, jsonschema
#sys.path.append(os.path.join(thispath,'..'))

parser = argparse.ArgumentParser()
parser.add_argument('transcfile', type=str)
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

assert os.path.isfile(args.transcfile), args.transcfile
assert args.transcfile.endswith('.json'), args.transcfile
with open(args.transcfile,'r') as infile:
    trdat = json.load(infile)

# {"word_count":N, "total_duration":M, "transcript":[...]}

tschema = {"type":"object", "properties": {  \
        "word_count": {"type":"number"},     \
        "total_duration": {"type":"number"}, \
        "transcript": {"type":"array"}  }} #, "items":{"type":"number"}},

jsonschema.validate(trdat, tschema)

newj = {"word_count":0, "total_duration":int(round(args.trimduration)), \
        "transcript":[]}
# word_count, duration, Array of sentences
# Array of words, start, end 
firstword = True
for sdic in trdat['transcript']:
    assert len(sdic) == 3, str(sdic)
    assert isinstance(sdic[1],float), str(sdic)
    assert isinstance(sdic[2],float), str(sdic)
    keepsentc = []
    for word in sdic[0]:
        assert isinstance(word,dict), str(type(word))
        assert tuple(sorted(word.keys())) == ('d','e','n','t'), str(word.keys())
        if word['t'] >= args.trimstart and word['e'] <= args.trimend:
            if firstword:
                print("BEF: word ---- "+str(word))
            word['t'] = round(float(word['t'] - args.trimstart), 3)
            word['e'] = round(float(word['e'] - args.trimstart), 3)
            if firstword:
                print("AFT: word ---- "+str(word))
                firstword = False
            keepsentc.append(word)
    if len(keepsentc) > 0:
        mint = min((word['t'] for word in keepsentc))
        maxt = max((word['e'] for word in keepsentc))
        newj["transcript"].append([keepsentc, mint, maxt])
        newj["word_count"] += int(len(keepsentc))
        #newj["total_duration"] += float(maxt) - float(mint)

newj["total_duration"] = args.trimduration
    #round(newj["total_duration"],3)

print("ok")

if len(args.outfile) <= 1:
    args.outfile = args.transcfile[:-len('.json')]+'_trimmed.json'
with open(args.outfile,'w') as outfile:
    json.dump(newj, outfile)
