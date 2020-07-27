import os
from copy import deepcopy
import argparse
import json

# TODO: jsonschema


#
# example (result will be two slides: half of slide2 and half of slide3)
#
#
#    t=0              start_offset           newstart         newend               end_offset    videoend
#     |                     |           *       |        *       |      *              |             |
#                           ----slide1---                -----slide3-----
#                                       ------slide2------              -----slide4-----


def fix_hack_start_offset(time_:float):
    if time_ <= 0.001001:
        print("HACK: when start_offset==0.001, adjusting to 0, since assuming the 0.001 was a hack")
        return 0.
    return time_

def trim_powerpoint_slides_of_lecture(thejson:dict, newstart:float, newend:float):
    assert newstart >= 0., str(newstart)
    assert newend > newstart, str(newstart)+' '+str(newend)
    assert 'allId' in thejson and 'byId' in thejson, str(thejson.keys())
    print("\n")
    if 'start_offset' in thejson:
        assert thejson['start_offset'] < newend, str(thejson['start_offset'])+' vs '+str(newend)
        old_start_offset = fix_hack_start_offset(float(deepcopy(thejson['start_offset'])))
        new_start_offset = max(0., old_start_offset - newstart)
        thejson['start_offset'] = max(0.001, new_start_offset)
    else:
        old_start_offset = 0.
        new_start_offset = 0.
    if 'end_offset' in thejson:
        assert thejson['end_offset'] > newstart, str(thejson['end_offset'])+' vs '+str(newstart)
        thejson['end_offset'] = max(0.001, float(thejson['end_offset'])-newstart)
    thejson['totalDuration'] = newend - newstart
    print("newstart "+str(newstart)+", newend "+str(newend)+"; old_start_offset "+str(old_start_offset)+", new_start_offset "+str(new_start_offset))
    newById   = {}
    newAllId  = []
    vids2trim = []
    vidkeysbeingtrimmed = {}
    for slid in thejson['allId']:
        slstart = fix_hack_start_offset(thejson['byId'][slid]['start']) + old_start_offset
        slend   = thejson['byId'][slid]['end']   + old_start_offset
        if slstart < newend and slend > newstart: # else the slide should be deleted
            if slstart < newstart or slend > newend: # the slide needs to be trimmed
                if slstart < newstart:
                    new_start_offset += float(newstart - slstart)
                    print("new_start_offset: "+str(new_start_offset))
                slide_new_start = max(newstart, slstart)
                slide_new_end   = min(newend,   slend)
                assert slide_new_end > slide_new_start, str(slide_new_start)+' !< '+str(slide_new_end)
                newAllId.append(slid)
                newById[slid] = deepcopy(thejson['byId'][slid])
                newById[slid]['start'] = max(0.001, slide_new_start - new_start_offset)
                newById[slid]['end']   =            slide_new_end   - new_start_offset
                for key,val in newById[slid].items():
                    if 'embed' in key.lower() and isinstance(val,str) and len(val) > 4 and val.endswith('.mp4'):
                        videosplit = val.split('/')
                        oldloc = videosplit[-1]
                        newfname = oldloc[:oldloc.rfind('.')]+'_trimmed.mp4'
                        prefolder = ''
                        if len(videosplit) > 1:
                            prefolder = videosplit[-2] + '/'
                        appendme = {"oldfile":val, "newfile":newfname, "oldloc": oldloc, "prefolder": prefolder, "-ss":max(0., newstart - slstart), "-to":min(newend - slstart, slend - slstart)}
                        if val not in vidkeysbeingtrimmed:
                            vidkeysbeingtrimmed[val] = appendme
                            vids2trim.append(appendme)
                            print("video trim job:\n"+str(appendme))
                        else:
                            assert abs(vidkeysbeingtrimmed[val]["-ss"] - appendme["-ss"]) < 1e-6 \
                               and abs(vidkeysbeingtrimmed[val]["-to"] - appendme["-to"]) < 1e-6 \
                                   and vidkeysbeingtrimmed[val]['newfile'] == appendme['newfile'], \
                                str(vidkeysbeingtrimmed[val])+' vs '+str(appendme)
                        newById[slid][key] = newfname
            else: # no trimming
                newAllId.append(slid)
                newById[slid] = deepcopy(thejson['byId'][slid])
                newById[slid]['start'] = max(0.001, newById[slid]['start'] - new_start_offset)
                newById[slid]['end']   -= new_start_offset

            newById[slid]['duration'] = newById[slid]['end'] - newById[slid]['start']
            assert newById[slid]['duration'] > 1e-6, str(newById[slid]['duration'])
            print("** slide \'"+str(slid)+"\' start-->end: "+str( newById[slid]['start'] )+" --> "+str( newById[slid]['end'] ))
        else:
            print("deleting slide "+str(slid))
            new_start_offset += float(slend - slstart)
            print("new_start_offset: "+str(new_start_offset))

    thejson['byId'] = newById
    thejson['allId'] = newAllId

    print("\n")
    return thejson, vids2trim
