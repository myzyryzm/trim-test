#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
import json
import re, requests
from requests.auth import HTTPBasicAuth
sys.path.append(os.path.join(thispath,'..'))

# TODO: HOW TO PASS VARIABLES [start with environmental then encrypted environmental?]
identity_basic_ = {}
identity_basic_['django_url'] = os.environ.get('DJANGO_URL', '')
identity_basic_['django_user'] = os.environ.get('DJANGO_USER', '')
identity_basic_['django_pass'] = os.environ.get('DJANGO_PASS', '')

def trim_trailing_slash(somepath: str):
    while somepath.endswith('/') and len(somepath) > 0:
        somepath = somepath[:-1]
    return somepath

def my_raise_for_status(req):
    try:
        req.raise_for_status()
    except requests.exceptions.HTTPError as ee:
        print("failed request: response:\n"+str(req.text))
        try:
            print(str(req.json()))
        except json.decoder.JSONDecodeError:
            pass
        raise ee

django_rest_lecture_update = \
       {'url': trim_trailing_slash(identity_basic_['django_url'])+'/lecture_field_value', \
 'ppjPostURL': trim_trailing_slash(identity_basic_['django_url'])+'/lecture_ppj_value', \
     'auth': (identity_basic_['django_user'], \
              identity_basic_['django_pass']), \
    }
       
def build_getter_poster_for_univ2lect(bucket:str, univ2lect:str):
    assert univ2lect.count('/') == 3, str(univ2lect)
    univ2lect = univ2lect.split('/')
    assert min([len(ss) for ss in univ2lect]) > 1, str(univ2lect)

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
