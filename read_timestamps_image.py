#!/usr/bin/env python
import os,sys,time
import numpy as np
import png # png from: pip install pypng

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
