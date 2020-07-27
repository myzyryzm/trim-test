import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
import json, jsonschema
import re, requests
from requests.auth import HTTPBasicAuth
sys.path.append(os.path.join(thispath,'..'))
from utils import subprocess_call, subprocess_check_output, fstr, s3_upload_file, s3_download_file
from django_utils import build_getter_poster_for_univ2lect
from trim_notes import download_and_trim_contours
from trim_slides import trim_powerpoint_slides_of_lecture

parser = argparse.ArgumentParser()
parser.add_argument('bucket',    type=str)
parser.add_argument('univ2lect', type=str, help='e.g. ucsd/spring17/math20c/lecture4')
parser.add_argument('-ss', '--trimstart',    type=float, required=True)
parser.add_argument('-te', '--trimend',      type=float, default=-1.)
parser.add_argument('-td', '--trimduration', type=float, default=-1.)
parser.add_argument('--refilter', action='store_true')
parser.add_argument('--pickle_params', type=str, default='', help='pickle filter')
args = parser.parse_args()

TRIM_SLIDES = os.environ.get('TRIM_SLIDES', 1)
TRIM_SLIDES = False if TRIM_SLIDES is '0' else True

TRIM_TRANSCRIPT = os.environ.get('TRIM_TRANSCRIPT', 1)
TRIM_TRANSCRIPT = False if TRIM_TRANSCRIPT is '0' else True

TRIM_NOTES = os.environ.get('TRIM_NOTES', 1)
TRIM_NOTES = False if TRIM_NOTES is '0' else True

# TODO : DO WE NEED SEPARATE FOR TRACKING AND NOTES
TRIM_TRACKING = os.environ.get('TRIM_TRACKING', 1)
TRIM_TRACKING = False if TRIM_TRACKING is '0' else True

TRIM_VIDEO = os.environ.get('TRIM_VIDEO', 1)
TRIM_VIDEO = False if TRIM_VIDEO is '0' else True

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

univ2lect_key = args.univ2lect
bucket = args.bucket
assert args.univ2lect.count('/') == 3, str(args.univ2lect)
univ2lect = args.univ2lect.split('/')
assert min([len(ss) for ss in univ2lect]) > 1, str(univ2lect)

#------------------------------------------------------------------
tmpdir = f'{thispath}/tmp'
subprocess_call(['mkdir','-p', tmpdir])
filesintmp_ = list([os.path.join(tmpdir,ff) for ff in os.listdir(tmpdir)])
if len(filesintmp_) > 0:
    subprocess_call(['rm','-rf',]+filesintmp_)
tmpdir += '/'
#------------------------------------------------------------------

getorpostcontent, s3urlbase = build_getter_poster_for_univ2lect(args.bucket, '/'.join(univ2lect))

fielddat = {ff:getorpostcontent(ff) for ff in ('time_block', 'transcript', 'tracking_data', 'video', 'enhanced_video', 'powerpointjson')}
vids2trim = []

if TRIM_SLIDES is True:
    if len(fielddat['powerpointjson']) > 4:
        ppj = fielddat['powerpointjson'].replace('\\\"','\"')
        ppj = json.loads(ppj)
        newppj, vids2trim = trim_powerpoint_slides_of_lecture(thejson=ppj, newstart=args.trimstart, newend=args.trimend)
        print('newppj', newppj)
        getorpostcontent('powerpointjson', newppj)
else:
    print('skipping slides')

if TRIM_TRANSCRIPT is True:
    if len(fielddat['transcript']) > 4:
        in_file = fielddat['transcript']
        dl_path = f'{tmpdir}/{in_file}'
        full_key = f'{univ2lect_key}/{in_file}'
        s3_download_file(bucket, full_key, dl_path)
        
        assert 0 == subprocess_call(['python3',os.path.join(thispath,'trim_transcript.py'),tmpdir+fielddat['transcript'], '-ss',str(args.trimstart),'-te',str(args.trimend)])
        
        out_file = fielddat['transcript'][:-len('.json')]   +'_trimmed.json'
        out_path = f'{tmpdir}/{out_file}'
        assert os.path.isfile(out_path), out_path
        
        getorpostcontent('transcript',    fielddat['transcript'][:-len('.json')]   +'_trimmed.json')
        full_key = f'{univ2lect_key}/{out_file}'
        s3_upload_file(bucket, full_key, out_path)
    else:
        print("====================================== warning: no transcript for "+str(univ2lect))
else:
    print('skipping transcript')
    
if TRIM_NOTES is True:
    if len(fielddat['time_block']) > 0:
        assert fielddat['time_block'].count('/') == 1, str(fielddat['time_block'])
        fielddat['time_block'], timeblockmetajson = fielddat['time_block'].split('/') # split "TB1/meta.json" --> "TB1", "meta.json"
        in_folder = fielddat['time_block']
        dl_path = f'{tmpdir}{in_folder}'
        subprocess_call(['mkdir','-p', dl_path])
        filesintmp_ = list([os.path.join(dl_path,ff) for ff in os.listdir(dl_path)])
        if len(filesintmp_) > 0:
            subprocess_call(['rm','-rf',]+filesintmp_)
            
        full_key = f'{univ2lect_key}/{in_folder}/'
        outnotesfold = download_and_trim_contours(bucket, full_key, dl_path, 
                                   trimstart=args.trimstart, trimend=args.trimend, **dargs)
        getorpostcontent('time_block', outnotesfold+'/'+timeblockmetajson)
        print("outnotesfold == "+str(outnotesfold))
    else:
        print("====================================== warning: no notes for "+str(univ2lect))
else:
    print('skipping notes')

if TRIM_TRACKING is True:
    if len(fielddat['tracking_data']) > 4:
        in_file = fielddat['tracking_data']
        dl_path = f'{tmpdir}/{in_file}'
        full_key = f'{univ2lect_key}/{in_file}'
        s3_download_file(bucket, full_key, dl_path)
        
        subprocess_check_output(['python3',os.path.join(thispath,'trim_tracking_json.py'), tmpdir+fielddat['tracking_data'],'-ss',str(args.trimstart),'-te',str(args.trimend)])
        
        out_file = fielddat['tracking_data'][:-len('.json')]   +'_trimmed.json'
        out_path = f'{tmpdir}/{out_file}'
        assert os.path.isfile(out_path), out_path
        
        getorpostcontent('tracking_data', fielddat['tracking_data'][:-len('.json')]+'_trimmed.json')
        full_key = f'{univ2lect_key}/{out_file}'
        s3_upload_file(bucket, full_key, out_path)
    else:
        print("====================================== warning: no tracking for "+str(univ2lect))
else:
    print('skipping tracking')

if TRIM_VIDEO is True:
    for videofield in ('video', 'enhanced_video'):
        if videofield in fielddat and len(fielddat[videofield]) > 1:
            videosplit = fielddat[videofield].split('/')
            oldloc = videosplit[-1]
            newvideoname = oldloc[:-4]+'_trimmed'+oldloc[-4:]
            prefolder = ''
            if len(videosplit) > 1:
                prefolder = videosplit[-2] + '/'
            
            vids2trim.append({
                "oldfile":fielddat[videofield], 
                "newfile":newvideoname, 
                "oldloc": oldloc, 
                "prefolder": prefolder,
                "-ss":args.trimstart,
                "-to":args.trimend, 
                "videofield":videofield
            })
            # fielddat[videofield]=video_ece_265a_a00_jan_13_le_hybrid_tcns.mp4
        else:
            print("no "+str(videofield)+" to trim for this lecture")
else:
    print('skipping video')
    
for videototrim in vids2trim:
    print("trimming video \'"+str(videototrim["oldfile"])+"\'")
    assert videototrim["oldfile"][-4] == '.', str(videototrim["oldfile"])
    oldvideoname=videototrim["oldfile"]
    newvideoname=videototrim["newfile"]
    oldloc = videototrim["oldloc"]
    
    full_key = f'{univ2lect_key}/{oldvideoname}'
    file_in = f'{tmpdir}{oldloc}'
    file_out = f'{tmpdir}{newvideoname}'
    time_start = videototrim["-ss"]
    time_durat = videototrim["-to"] - time_start
    
    s3_download_file(bucket, full_key, file_in)
    
    ffmpeg = ['ffmpeg','-y', '-i', file_in, '-ss', fstr(time_start), '-t', fstr(time_durat), \
                                    '-vcodec','copy', '-acodec','copy', file_out]
    subprocess_check_output(ffmpeg)
    
    prefolder = videototrim["prefolder"]
    full_key = f'{univ2lect_key}/{prefolder}{newvideoname}'
    s3_upload_file(bucket, full_key, file_out)
    
    if "videofield" in videototrim:
        getorpostcontent(videototrim['videofield'], newvideoname)