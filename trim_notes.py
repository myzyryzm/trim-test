#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
from copy import copy
import json, jsonschema
import re
import numpy as np
import png # pip install pypng
sys.path.append(os.path.join(thispath,'..'))
from utils import subprocess_check_output, subprocess_call, describe, s3_download_folder, s3_upload_folder

def read_timestamps_image(tspath_, compareshape=None):
    assert os.path.isfile(tspath_), tspath_
    # read timestamps
    with open(tspath_,'rb') as tsopenedfile:
        reader = png.Reader(file=tsopenedfile)
        readdata = reader.read()
        tsimg = np.vstack([np.uint16(row) for row in readdata[2]])
        assert tsimg.shape[1] == readdata[0], str(tsimg.shape)+', '+str(readdata[:2])
        assert tsimg.shape[0] == readdata[1], str(tsimg.shape)+', '+str(readdata[:2])
        if compareshape is not None:
            assert list(tsimg.shape[:2]) == list(compareshape[:2]), str(tsimg.shape)+', '+str(compareshape)
    assert isinstance(tsimg, np.ndarray), str(type(tsimg))
    assert len(tsimg.shape) == 2 and tsimg.size > 1, str(tsimg.shape)
    return tsimg

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

def download_and_trim_contours(bucket:str, key: str, localpath: str, trimstart:float=-1., trimend:float=-1., trimduration:float=-1., \
                                outdir:str='', refilter:bool=False, pickle_params:str=''):
   
    s3_download_folder(bucket, key, localpath)

    if trimend < 0. and trimduration < 0.:
        trimend      = int(1e9)
        trimduration = int(1e9)
    else:
        assert not (trimend > 0. and trimduration > 0.), 'use one or the other'
        if trimduration > 0.:
            trimend = trimstart + trimduration
        else:
            trimduration = trimend - trimstart
            assert trimduration > 0., str(trimend)+', '+str(trimstart)

    tsfileend = '_timestamps.png'

    #----------------------
    tmpdir = localpath
    while tmpdir.endswith('/'):
        tmpdir = tmpdir[:-1]
    subprocess_call(['mkdir','-p', tmpdir])

    #----------------------
    basecf = localpath.split('/')[-1]
    backupbaseblockfold = copy(basecf)
    if len(outdir) < 1:
        ival = None
        if '_' in basecf:
            try:
                ival = int(basecf.split('_')[-1])
            except ValueError:
                pass
        if isinstance(ival,int):
            ival += 1
            basecf = '_'.join(basecf.split('_')[:-1])+'_'+str(ival)
            # TODO: s3 head to check if this folder exists already
            print("ayyy: "+str(ival))
        else:
            basecf += '_0'
        outdir = basecf

    assert '/' not in outdir, str(outdir)

    print("outdir: "+str(outdir))
    
    localoutdir = os.path.join(os.path.dirname(tmpdir), outdir)
    subprocess_call(['mkdir','-p', localoutdir])
    
    univ2lect = '/'.join(key.split('/')[:-2])
    full_key = f'{univ2lect}/{outdir}'
    
    print("localoutdir: "+str(localoutdir))
    print("s3 out key: "+str(full_key))
    
    pngs = [os.path.join(tmpdir,ff) for ff in os.listdir(tmpdir) if ff.endswith(tsfileend)]
    assert len(pngs) > 0, str(pngs)+'\n'+str(list(os.listdir(tmpdir)))
    
    subtrme = int(round(float(trimstart)))
    maxtime = int(round(float(trimend  )))
    
    syncme = []

    for pngf in pngs:
        img = read_timestamps_image(pngf)
        assert isinstance(img,np.ndarray), str(type(img))
        assert len(img.shape) == 2, str(img.shape)
        describe(os.path.basename(pngf), img)
        if np.amin(img) > int(round(trimend)):
            continue
        # TODO: if we know erase times, remove contours which were erased before "trimstart"
        img[img<subtrme] = subtrme
        img[img>maxtime] = maxtime # TODO: this is needlessly destructive; but fixes potential frontend bugs (seek past end of video?)
        img -= subtrme

        writer = png.Writer(width=img.shape[1], height=img.shape[0], greyscale=True, alpha=False, bitdepth=16, compression=5)
        outfname = os.path.join(localoutdir,os.path.basename(pngf))
        syncme.append(outfname)
        with open(outfname, 'wb') as openedfile:
            writer.write(openedfile, img)
            
    for fpth in syncme:
        oldimgf = os.path.join(os.path.dirname(fpth), os.path.basename(fpth)[:-len(tsfileend)])
        oldfs = [os.path.join(tmpdir,ff) for ff in os.listdir(tmpdir) if not ff.endswith(tsfileend) and ff.startswith(os.path.basename(oldimgf))]
        assert len(oldfs) == 1, str(oldimgf)+'\n'+str(oldfs)
        oldfs = oldfs[0]
        subprocess_check_output(['cp', oldfs, localoutdir+'/'])
    
    metafiles = [os.path.join(tmpdir,ff) for ff in os.listdir(tmpdir) if ff.lower().startswith('meta') and ff.lower().endswith('.json')]
    
    for ff in metafiles:
        print("in meta.json, replacing \'"+str(backupbaseblockfold)+"\' with \'"+str(outdir)+"\'")
        replace_folder_in_metafile(ff, localoutdir+'/'+os.path.basename(ff), backupbaseblockfold, outdir)
    
    # TODO: ADD THIS FUNCTIONALITY BACK
    test_it = False
    if refilter and test_it is True:
        filterfile = '/evt/interactive-writing-segmentation/filter_keyframes.py'
        assert os.path.isfile(filterfile), filterfile
        fargs = ['python',filterfile,localoutdir,'--were_transparency_on_s3','--overwrite_in_place']
        if len(pickle_params) > 1:
            fargs += ['--autorun','--pickle_params',pickle_params]
        assert 0 == subprocess_call(fargs)

    print("syncing resulting folder")
    
    while full_key.endswith('/'):
        full_key = full_key[:-1]
    
    s3_upload_folder(bucket, full_key, localoutdir)
    return outdir
