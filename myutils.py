import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import re
import subprocess

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

