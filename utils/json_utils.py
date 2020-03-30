
from flask.json import JSONEncoder

from utils.printable import Printable


class MyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, Printable):
            return obj.__dict__
        # return JSONEncoder.default(self, obj)
