import ecdsa

from params import Params
from utils.hash_utils import convert_pubkey_to_addr, build_message


class Wallet:
    """
    管理公私钥对、地址的密钥对
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

    @classmethod
    def create_signature(self, pk, pointer, tx_out):
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
