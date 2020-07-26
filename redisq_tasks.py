#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
import base64
import boto3
# uploading is a local task, using redis queue
sys.path.append(os.path.join(thispath,'..'))
from myutils import subprocess_check_output, fstr

# TODO: use boto, check if file exists, check hash/etag if it does (so don't re-download)
aws_s3_prefix = 's3://'

def aws_s3_download(s3path: str, localpath: str, skip_if_exist_and_skip_hash_check:bool=False, sync:bool=False):
    assert s3path.startswith(aws_s3_prefix), s3path
    if os.path.isfile(localpath) and os.path.getsize(localpath) > 0:
        if not skip_if_exist_and_skip_hash_check:
            print("TODO: CHECK HASH/ETAG... re-downloading "+str(localpath)+" ?")
    assert not localpath.startswith(aws_s3_prefix), localpath
    cpcmd = 'cp'
    if sync:
        cpcmd = 'sync'
    call_cmd = ['aws','s3',cpcmd,'--only-show-errors'] + [s3path, localpath]
    subprocess_check_output(call_cmd, assert_hard=True)

def aws_s3_upload(localpath: str, s3path: str, sync:bool=False, delete_after_up:bool=False):
    assert s3path.startswith(aws_s3_prefix), s3path
    assert not localpath.startswith(aws_s3_prefix), localpath
    if sync:
        cpcmd = 'sync'
        assert os.path.exists(localpath), str(localpath)
    else:
        cpcmd = 'cp'
        assert os.path.isfile(localpath), str(localpath)
    call_cmd = ['aws','s3',cpcmd,'--only-show-errors'] + [localpath, s3path]
    subprocess_check_output(call_cmd, assert_hard=True)
    if delete_after_up:
        subprocess_check_output(['rm', '-f', localpath])
