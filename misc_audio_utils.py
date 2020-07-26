import os
import numpy as np


# significant figures when printing
round_to_n = lambda x, n: round(x, -int(np.floor(np.log10(np.fabs(x)))) + (n - 1))
def fstr(input, dig=4):
    if np.fabs(input) < 1e-20:
        return '0'
    try:
    	return str(round_to_n(input, dig))
    except OverflowError:
        return str(round(float(input),dig))
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

