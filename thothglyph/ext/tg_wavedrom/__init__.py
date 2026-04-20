import json
import yaml

from . import bitfield


def parse(text):
    yaml_obj = yaml.load(text, Loader=yaml.FullLoader)
    json_text = json.dumps(yaml_obj, indent=4)
    json_obj = json.loads(json_text)
    return json_obj
