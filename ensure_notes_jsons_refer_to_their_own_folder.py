#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
from copy import copy
import json, jsonschema
import numpy as np
import re, requests
sys.path.append(os.path.join(thispath,'..'))
from myutils import subprocess_check_output, subprocess_call
from django_lecture_field_get_or_post import build_getter_poster_for_univ2lect

def replace_folder_in_metafile(infile, outfile, oldstr, newstr):
    with open(infile,'r') as readme:
        indat = json.load(readme)
    assert isinstance(indat,dict), str(type(indat))+' '+str(infile)
    newd = {"meta":indat["meta"], "data":[]}
    assert isinstance(indat['data'],list), str(type(indat['data']))+'\n\n'+str(indat)+'\n'
    for key in indat['data']:
        assert isinstance(key,dict), str(type(key))
        if oldstr is not None and len(oldstr) > 0:
            assert      key["image"].startswith(oldstr) and      key["image"].count('/') == 1, str(key["image"])     +', '+str(oldstr)
            assert key["timestamps"].startswith(oldstr) and key["timestamps"].count('/') == 1, str(key["timestamps"])+', '+str(oldstr)
        key["image"]      = '/'.join((newstr,      key["image"].split('/')[-1]))
        key["timestamps"] = '/'.join((newstr, key["timestamps"].split('/')[-1]))
        newd["data"].append(copy(key))
    with open(outfile,'w') as outfile:
        json.dump(newd, outfile)


def download_and_check_meta(bucket:str, univ2lect:str):
    assert len(bucket) > 1, str(bucket)
    assert univ2lect.count('/') == 3, str(univ2lect)
    univ2lect = univ2lect.split('/')
    assert min([len(ss) for ss in univ2lect]) > 1, str(univ2lect)

    tmpdir_base = '/tmp/aws_s3_tmp_'
    tmpdir_intg = 0
    while os.path.isdir(tmpdir_base+str(tmpdir_intg)):
        tmpdir_intg += 1
    tmpdir = tmpdir_base+str(tmpdir_intg)
    while tmpdir.endswith('/'):
        tmpdir = tmpdir[:-1]
    subprocess_call(['mkdir','-p', tmpdir])

    getorpostcontent, s3urlbase = build_getter_poster_for_univ2lect(bucket, '/'.join(univ2lect))

    notesmeta = getorpostcontent('time_block')
    assert notesmeta.count('/') == 1, str(notesmeta)
    tmplocation = tmpdir+'/'+notesmeta.split('/')[-1]

    assert 0 == subprocess_call(['aws','s3','cp', s3urlbase+notesmeta, tmplocation])
    replace_folder_in_metafile(tmplocation, tmplocation, None, notesmeta.split('/')[0])
    assert 0 == subprocess_call(['aws','s3','cp', tmplocation, s3urlbase+notesmeta])
