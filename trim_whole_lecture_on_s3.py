#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
import json, jsonschema
import re, requests
from requests.auth import HTTPBasicAuth
sys.path.append(os.path.join(thispath,'..'))
from myutils import subprocess_call, subprocess_check_output, fstr
from redisq_tasks import aws_s3_download, aws_s3_upload
from django_lecture_field_get_or_post import build_getter_poster_for_univ2lect
from download_and_trim_contours import download_and_trim_contours
from trim_powerpoint_slides_of_lecture import trim_powerpoint_slides_of_lecture

parser = argparse.ArgumentParser()
parser.add_argument('bucket',    type=str)
parser.add_argument('univ2lect', type=str, help='e.g. ucsd/spring17/math20c/lecture4')
parser.add_argument('-ss', '--trimstart',    type=float, required=True)
parser.add_argument('-te', '--trimend',      type=float, default=-1.)
parser.add_argument('-td', '--trimduration', type=float, default=-1.)
parser.add_argument('--refilter', action='store_true')
parser.add_argument('--pickle_params', type=str, default='', help='pickle filter')
args = parser.parse_args()

dargs = {}
if args.refilter:
    dargs['refilter'] = True
if len(args.pickle_params) > 0:
    assert args.refilter
    dargs['pickle_params'] = args.pickle_params

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

assert args.univ2lect.count('/') == 3, str(args.univ2lect)
univ2lect = args.univ2lect.split('/')
assert min([len(ss) for ss in univ2lect]) > 1, str(univ2lect)

#------------------------------------------------------------------
tmpdir_base = f'{thispath}/tmp/aws_s3_tmp_'
tmpdir_intg = 0
while os.path.isdir(tmpdir_base+str(tmpdir_intg)):
    tmpdir_intg += 1
tmpdir = tmpdir_base+str(tmpdir_intg)
while tmpdir.endswith('/'):
    tmpdir = tmpdir[:-1]
subprocess_call(['mkdir','-p', tmpdir])
filesintmp_ = list([os.path.join(tmpdir,ff) for ff in os.listdir(tmpdir)])
if len(filesintmp_) > 0:
    subprocess_call(['rm','-rf',]+filesintmp_)
tmpdir += '/'
#------------------------------------------------------------------

getorpostcontent, s3urlbase = build_getter_poster_for_univ2lect(args.bucket, '/'.join(univ2lect))

fielddat = {ff:getorpostcontent(ff) for ff in ('time_block', 'transcript', 'tracking_data', 'video', 'enhanced_video', 'powerpointjson')}

if len(fielddat['powerpointjson']) > 4:
    ppj = fielddat['powerpointjson'].replace('\\\"','\"')
    ppj = json.loads(ppj)
    newppj, vids2trim = trim_powerpoint_slides_of_lecture(thejson=ppj, newstart=args.trimstart, newend=args.trimend)
    print('newppj', newppj)
    getorpostcontent('powerpointjson', newppj)
else:
    vids2trim = []

if len(fielddat['transcript']) > 4:
    aws_s3_download(s3urlbase+fielddat['transcript'], tmpdir)
    assert 0 == subprocess_call(['python',os.path.join(thispath,'trim_transcript.py'),tmpdir+fielddat['transcript'], '-ss',str(args.trimstart),'-te',str(args.trimend)])
    trimout_transc = tmpdir+fielddat['transcript'][:-len('.json')]   +'_trimmed.json'
    assert os.path.isfile(trimout_transc), trimout_transc
    getorpostcontent('transcript',    fielddat['transcript'][:-len('.json')]   +'_trimmed.json')
    aws_s3_upload(trimout_transc, s3urlbase)
else:
    print("====================================== warning: no transcript for "+str(univ2lect))

if len(fielddat['tracking_data']) > 4:
    aws_s3_download(s3urlbase+fielddat['tracking_data'], tmpdir)
    subprocess_check_output(['python',os.path.join(thispath,'trim_tracking_json.py'), tmpdir+fielddat['tracking_data'],'-ss',str(args.trimstart),'-te',str(args.trimend)])
    trimout_tracki = tmpdir+fielddat['tracking_data'][:-len('.json')]+'_trimmed.json'
    assert os.path.isfile(trimout_tracki), trimout_tracki
    getorpostcontent('tracking_data', fielddat['tracking_data'][:-len('.json')]+'_trimmed.json')
    aws_s3_upload(trimout_tracki, s3urlbase)
else:
    print("====================================== warning: no tracking for "+str(univ2lect))

if len(fielddat['time_block']) > 0:
    assert fielddat['time_block'].count('/') == 1, str(fielddat['time_block'])
    fielddat['time_block'], timeblockmetajson = fielddat['time_block'].split('/') # split "TB1/meta.json" --> "TB1", "meta.json"

    outnotesfold = download_and_trim_contours(s3urlbase+fielddat['time_block'], syncdir=tmpdir+fielddat['time_block'], trimstart=args.trimstart, trimend=args.trimend, **dargs)
    getorpostcontent('time_block', outnotesfold+'/'+timeblockmetajson)
    print("outnotesfold == "+str(outnotesfold))
else:
    print("====================================== warning: no notes for "+str(univ2lect))

assert s3urlbase.startswith('s3://'), s3urlbase
s3noprefix = s3urlbase[ len('s3://'):]

for videofield in ('video', 'enhanced_video'):
    if videofield in fielddat and len(fielddat[videofield]) > 1:
        oldloc = fielddat[videofield].split('/')[-1]
        newvideoname = oldloc[:-4]+'_trimmed'+oldloc[-4:]
        
        vids2trim.append(
            {
                "oldfile":fielddat[videofield], 
                "newfile":newvideoname, 
                "oldloc": oldloc, 
                "-ss":args.trimstart,
                "-to":args.trimend, 
                "videofield":videofield
            }
        )
        # fielddat[videofield]=video_ece_265a_a00_jan_13_le_hybrid_tcns.mp4
    else:
        print("no "+str(videofield)+" to trim for this lecture")

for videototrim in vids2trim:
    print("trimming video \'"+str(videototrim["oldfile"])+"\'")
    assert videototrim["oldfile"][-4] == '.', str(videototrim["oldfile"])
    oldvideoname=videototrim["oldfile"]
    newvideoname=videototrim["newfile"]
    oldloc = videototrim["oldloc"]
    
    aws_s3_download(f'{s3urlbase}{oldvideoname}', tmpdir)
    file_in = f'{tmpdir}{oldloc}'
    file_out = f'{tmpdir}{newvideoname}'
    time_start = videototrim["-ss"]
    time_durat = videototrim["-to"] - time_start
    ffmpeg = ['ffmpeg','-y', '-i', file_in, '-ss', fstr(time_start), '-t', fstr(time_durat), \
                                    '-vcodec','copy', '-acodec','copy', file_out]
    
    subprocess_check_output(ffmpeg)
    
    aws_s3_upload(file_out, s3urlbase)
    
    if "videofield" in videototrim:
        getorpostcontent(videototrim['videofield'], newvideoname)