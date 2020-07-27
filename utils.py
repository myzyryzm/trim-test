import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import re
import subprocess
import numpy as np
import boto3
from botocore.client import ClientError
sys.path.append(os.path.join(thispath,'..'))

s3 = boto3.client('s3')
s3_resource = boto3.resource('s3')

def s3_download_folder(bucket: str, key: str, localpath: str):
    s3_bkt = s3_resource.Bucket(bucket)
    for obj in s3_bkt.objects.filter(Prefix = key):
        filename = obj.key.split('/')[-1]
        full_path = f'{localpath}/{filename}'
        full_key=f'{key}{filename}'
        s3_download_file(bucket, full_key, full_path)
        
def s3_download_file(bucket: str, key: str, localpath: str):
    try:
       resp = s3.download_file(bucket, key, localpath)
       return 200
    except:
        print(f'unable to upload {localpath} to {bucket}/{key}') 
        return 400

def s3_upload_folder(bucket: str, key: str, localpath: str):
    files = [os.path.join(localpath, ff) for ff in os.listdir(localpath)]
    for file in files:
        filename = os.path.basename(file)
        full_key = f'{key}/{filename}'
        s3_upload_file(bucket, full_key, file)

def s3_upload_file(bucket: str, key: str, localpath: str):
    try:
       resp = s3.upload_file(localpath, bucket, key)
       return 200
    except:
        print(f'unable to upload {localpath} to {bucket}/{key}') 
        return 400

def fstr(somestr):
    return str(round(float(somestr),3))

def subprocess_check_output(args, kwargs={}, assert_hard=False, printcmd:bool=True):
    assert isinstance(args,list) or isinstance(args,tuple), str(type(args))
    if 'stderr' not in kwargs:
        kwargs['stderr'] = subprocess.STDOUT
    if printcmd:
        print("running: \'"+str(' '.join(args))+"\'")
    try:
        ret = subprocess.check_output(args, **kwargs) # return code would always be zero, would fail otherwise
    except subprocess.CalledProcessError as eee:
        mymsg = "failed command:\n"+str(args)+"\n================\n" \
               +str(eee.output.decode('utf-8'))+"\n================\n"
        if assert_hard:
            assert 0, mymsg
        ret = "WARNING: subprocess_check_output: "+mymsg
        print(ret)
        #raise subprocess.CalledProcessError
    if isinstance(ret,bytes):
        return ret.decode('utf-8')
    return ret

def subprocess_call(args, kwargs={}, assert_hard=False):
    assert isinstance(args,list) or isinstance(args,tuple), str(type(args))
    print("running: \'"+str(' '.join(args))+'\'')
    ccode = subprocess.call(args, **kwargs)
    if ccode != 0:
        prstr = "warning: return value "+str(ccode)+" != 0 from command\n"+str(args)+"\n"
        if assert_hard:
            assert 0, prstr
        else:
            print(prstr)
    return ccode

def check_dic1_has_all_keys_of_dic2(dic1, dic2):
    assert isinstance(dic1,dict), str(type(dic1))
    assert isinstance(dic2,dict), str(type(dic2))
    for key in dic2.keys():
        assert key in dic1.keys(), str(key)+', '+str(dic1.keys())

def check_dicts_have_same_keys(dic1, dic2):
    check_dic1_has_all_keys_of_dic2(dic1, dic2)
    check_dic1_has_all_keys_of_dic2(dic2, dic1)

# significant figures when printing
round_to_n = lambda x, n: round(x, -int(np.floor(np.log10(np.fabs(x)))) + (n - 1))

def f64fix(arr):
    if isinstance(arr,np.ndarray) and arr.dtype == np.float64:
        return np.float32(arr)
    return arr

def describe(name,arr,extranewline=None):
    prstr = str(name)
    try:
        prstr += ", shape "+str(arr.shape).replace(' ','')
    except AttributeError:
        try:
            prstr += ", shape "+str(arr.size()).replace(' ','')
            try:
                prstr += ", dtype "+str(arr.type()) # pytorch
            except (AttributeError,TypeError):
                prstr += ", dtype "+str(arr.data.type()) # pytorch
        except AttributeError:
            pass
    try:
        prstr += ", dtype "+str(arr.dtype)
    except AttributeError:
        pass

    try:
        arr32 = f64fix(arr)
        prstr += \
             ", (min,max) = ("+str(np.amin(arr32))+", "+str(np.amax(arr32))+")" \
            +", (mean,std) = ("+str(np.mean(arr32))+", "+str(np.std(arr32))+")" \
            +", median "+str(np.median(arr32))
        if arr.size <= 4:
            prstr += '\n'+str(f64fix(arr))
    except (TypeError, AttributeError, ValueError):
        if True: #not isinstance(arr,Variable):
            try:
                arrlen = len(arr)
                prstr += ", len = "+str(arrlen)
                MAXLEN = 8
                if arrlen <= MAXLEN:
                    ps1 = None
                    for ii in range(min(arrlen,MAXLEN)):
                        if ps1 is None:
                            ps1 = ""
                        else:
                            ps1 += ", "
                        ps1 += str(arr[ii])
                    if len(ps1) <= 150:
                        prstr += "    "+ps1
                    ps2 = ""
                    for ii in range(min(arrlen,MAXLEN)):
                        ps2 += "["+str(ii)+"]:"+str(type(arr[ii]))+" "
                    prstr += "    "+ps2
            except (AttributeError, TypeError, ValueError):
                prstr += ": type "+str(type(arr))

    if extranewline is not None:
        prstr += extranewline
    print(prstr)
    return prstr