#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
import json
import re, requests
from requests.auth import HTTPBasicAuth
sys.path.append(os.path.join(thispath,'..'))
from requests_utils import my_raise_for_status

def build_getter_poster_for_univ2lect(bucket:str, univ2lect:str, django_cred_dict:dict={}):
    assert univ2lect.count('/') == 3, str(univ2lect)
    univ2lect = univ2lect.split('/')
    assert min([len(ss) for ss in univ2lect]) > 1, str(univ2lect)

    if len(django_cred_dict.keys()) <= 0:
        from configslite import django_rest_lecture_update
    else:
        django_rest_lecture_update = django_cred_dict

    regstrip = lambda xx: re.sub('[^a-zA-Z0-9\_\-\.]+', '', xx)
    univ2lect = list([regstrip(ss) for ss in univ2lect])
    s3urlbase = 's3://'+bucket+'/'+'/'.join(univ2lect)+'/'

    fullURL = django_rest_lecture_update['url']+'/'+'/'.join(univ2lect)+'/'
    print(fullURL)
    ppjPostURL = django_rest_lecture_update['ppjPostURL']+'/'+'/'.join(univ2lect)+'/'
    basicauth = HTTPBasicAuth(*django_rest_lecture_update['auth'])

    def getorpostcontent(field, postcontent=None):
        ddic = {"fieldName": field}
        if postcontent is not None:
            return
            ddic["newValue"] = postcontent
            if isinstance(postcontent,dict):
                rr = requests.post(ppjPostURL, auth=basicauth, json=ddic)
            else:
                assert isinstance(postcontent,str), str(postcontent)
                rr = requests.post(fullURL, auth=basicauth, json=ddic)
        else:
            rr = requests.get(fullURL, auth=basicauth, json=ddic)
        my_raise_for_status(rr)
        return rr.text.strip('\"\\')

    return getorpostcontent, s3urlbase
