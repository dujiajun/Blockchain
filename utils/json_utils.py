from flask.json import JSONEncoder

from utils.printable import Printable


class MyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Printable):
            return obj.__dict__
