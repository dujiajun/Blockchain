import json

import ecdsa

from params import Params
from utils.hash_utils import convert_pubkey_to_addr, build_message
from utils.json_utils import MyJSONEncoder
from utils.printable import Printable


class Wallet(Printable):
    """
    管理公私钥对、地址的钱包
    """

    def __init__(self):
        self.pk = None
        self.sk = None
        self.addr = None

    def empty(self):
        """
        :return: 钱包是否存在
        """
        return self.addr is None

    def generate_key(self):
        """
        生成新的密钥对
        """
        self.sk = ecdsa.SigningKey.generate(curve=Params.CURVE)
        self.pk = self.sk.get_verifying_key()
        self.addr = convert_pubkey_to_addr(self.pk.to_string())

    def sign(self, message):
        return self.sk.sign(message)

    @classmethod
    def create_signature(cls, pk, pointer, tx_out):
        """
        创建签名
        :param pk: 公钥字符串
        :param pointer: 使用的UTXO的定位指针
        :param tx_out: 输出列表
        :return: 签名
        """
        string = str(pointer) + str(pk) + str(tx_out)
        signature = build_message(string)
        return signature

    def save_keys(self):
        if self.sk is None:
            return
        with open('wallet.txt', mode='w', encoding='utf-8') as f:
            f.write(self.sk.to_string().hex())

    def load_keys(self):
        with open('wallet.txt', mode='r', encoding='utf-8') as f:
            key = f.readlines()[0]
            self.sk = ecdsa.SigningKey.from_string(bytes.fromhex(key), curve=Params.CURVE)
            self.pk = self.sk.get_verifying_key()
            self.addr = convert_pubkey_to_addr(self.pk.to_string())


if __name__ == '__main__':
    wallet = Wallet()
    wallet.generate_key()
    wallet.save_keys()
    print(json.dumps(wallet, cls=MyJSONEncoder))
    wallet.generate_key()
    print(json.dumps(wallet, cls=MyJSONEncoder))
    wallet.load_keys()
    print(json.dumps(wallet, cls=MyJSONEncoder))