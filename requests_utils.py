import json
import requests

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
