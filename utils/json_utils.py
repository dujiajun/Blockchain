import ecdsa
from flask.json import JSONEncoder

from block import Block
from transaction import Vout, Tx
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
            # if isinstance(obj, Vin):
            #     obj_dict['sig_script'] = obj.sig_script
            if isinstance(obj, Vout):
                obj_dict['pubkey_script'] = obj.pubkey_script
            if isinstance(obj, Tx):
                obj_dict['is_coinbase'] = obj.is_coinbase
                obj_dict['id'] = obj.id
            if isinstance(obj, Block):
                obj_dict['hash'] = obj.hash
            return obj_dict
        # return JSONEncoder.default(self, obj)
