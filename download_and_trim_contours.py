#!/usr/bin/env python
import os,sys,time
thispath = os.path.dirname(os.path.abspath(__file__))
import argparse
from copy import copy
import json, jsonschema
import numpy as np
import png # pip install pypng
sys.path.append(os.path.join(thispath,'..'))
from myutils import subprocess_check_output, subprocess_call
from read_timestamps_image import read_timestamps_image
from misc_audio_utils import describe
from ensure_notes_jsons_refer_to_their_own_folder import replace_folder_in_metafile

def download_and_trim_contours(s3blocksdir:str, trimstart:float=-1., trimend:float=-1., trimduration:float=-1., \
                                syncdir:str='', outdir:str='', refilter:bool=False, pickle_params:str=''):
    while s3blocksdir.endswith('/'):
        s3blocksdir = s3blocksdir[:-1]

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

    assert s3blocksdir.startswith('s3://') and s3blocksdir.count('/') > 3, str(s3blocksdir)

    tsfileend = '_timestamps.png'

    #----------------------
    if len(syncdir) >= 1:
        tmpdir = syncdir
    else:
        tmpdir_base = '/tmp/aws_s3_tmp_'
        tmpdir_intg = 0
        while os.path.isdir(tmpdir_base+str(tmpdir_intg)):
            tmpdir_intg += 1
        tmpdir = tmpdir_base+str(tmpdir_intg)
    while tmpdir.endswith('/'):
        tmpdir = tmpdir[:-1]
    subprocess_call(['mkdir','-p', tmpdir])

    #----------------------
    basecf = s3blocksdir.split('/')[-1]
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
    s3outdir = '/'.join(s3blocksdir.split('/')[:-1]+[outdir,])

    subprocess_call(['mkdir','-p', localoutdir])

    print("localoutdir: "+str(localoutdir))
    print("s3 out dir: "+str(s3outdir))

    #----------------------

    assert 0 == subprocess_call(['aws','s3','sync', s3blocksdir, tmpdir])
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

    if refilter:
        filterfile = '/evt/interactive-writing-segmentation/filter_keyframes.py'
        assert os.path.isfile(filterfile), filterfile
        fargs = ['python',filterfile,localoutdir,'--were_transparency_on_s3','--overwrite_in_place']
        if len(pickle_params) > 1:
            fargs += ['--autorun','--pickle_params',pickle_params]
        assert 0 == subprocess_call(fargs)

    print("syncing resulting folder")
    assert 0 == subprocess_call(['aws','s3','sync', localoutdir, s3outdir])

    return outdir

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('s3blocksdir',  type=str, help='e.g. s3://evt-lect-test/ucsd/winter2018/math20b/lecture1/timeblocks1')
    parser.add_argument('-sd', '--syncdir',      type=str, default='')
    parser.add_argument('-o', '--outdir',  type=str, default='')

    parser.add_argument('-ss', '--trimstart',    type=float, required=True)
    parser.add_argument('-te', '--trimend',      type=float, default=-1.)
    parser.add_argument('-td', '--trimduration', type=float, default=-1.)

    parser.add_argument('--refilter', action='store_true')
    parser.add_argument('--pickle_params', type=str, default='', help='pickle filter')

    download_and_trim_contours(**vars(parser.parse_args()))
