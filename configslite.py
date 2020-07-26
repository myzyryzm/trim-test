import os

# TODO: HOW TO PASS VARIABLES [start with environmental then encrypted environmental?]
identity_basic_ = {}
identity_basic_['django_url'] = os.environ.get('DJANGO_URL', '')
identity_basic_['django_user'] = os.environ.get('DJANGO_USER', '')
identity_basic_['django_pass'] = os.environ.get('DJANGO_PASS', '')
print('identity_basic', identity_basic)
# this script won't do any asserts, so won't crash
# it's a subset of "configpaths.py"

def trim_trailing_slash(somepath: str):
    while somepath.endswith('/') and len(somepath) > 0:
        somepath = somepath[:-1]
    return somepath

django_rest_lecture_update = \
       {'url': trim_trailing_slash(identity_basic_['django_url'])+'/lecture_field_value', \
 'ppjPostURL': trim_trailing_slash(identity_basic_['django_url'])+'/lecture_ppj_value', \
     'auth': (identity_basic_['django_user'], \
              identity_basic_['django_pass']), \
    }
