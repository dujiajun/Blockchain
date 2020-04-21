import ecdsa
from flask.json import JSONEncoder

from blockchain.block import Block
from blockchain.transaction import Tx
from utils.printable import Printable


class MyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, ecdsa.SigningKey):
            return obj.to_string().hex()
        if isinstance(obj, ecdsa.VerifyingKey):
            return obj.to_string().hex()
        if isinstance(obj, Printable):
            obj_dict = obj.__dict__.copy()
            if isinstance(obj, Tx):
                obj_dict['is_coinbase'] = obj.is_coinbase
                obj_dict['id'] = obj.id
            if isinstance(obj, Block):
                obj_dict['hash'] = obj.hash
            return obj_dict
