import os
from typing import List

from utils.hash_utils import sha256d
from utils.printable import Printable


class Pointer(Printable):
    """
    输入单元中指向其金额来源的定位指针
    """

    def __init__(self, tx_id: str, n: int):
        """
        :param tx_id: 该输入单元的UTXO所在的交易编号
        :param n: 该输入单元的UTXO在其交易输出列表中的顺序
        """
        self.tx_id = tx_id
        self.n = n

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.tx_id == other.tx_id and self.n == other.n
        return False

    def __hash__(self):
        return hash((self.tx_id, self.n))


class Vin(Printable):
    """
    交易的输入单元
    """

    def __init__(self, to_spend: Pointer, signature: bytes, pubkey: bytes):
        """
        :param to_spend: 指向交易创建者的UTXO定位指针
        :param signature: 交易创建者的签名
        :param pubkey: 交易创建者的公钥
        """
        self.to_spend = to_spend
        self.signature = signature
        self.pubkey = pubkey

    @property
    def sig_script(self) -> bytes:
        """
        :return: 签名脚本（解锁脚本）
        """
        return self.signature + self.pubkey


class Vout(Printable):
    """
    交易的输出单元
    """

    def __init__(self, to_addr: str, value: int):
        """
        :param to_addr: 交易输出指向的地址
        :param value: 交易数量
        """
        self.to_addr = to_addr
        self.value = value

    @property
    def pubkey_script(self) -> str:
        """
        :return: 公钥脚本（锁定脚本）
        """
        return f"OP_DUP OP_ADDR {self.to_addr} OP_EQ OP_CHECKSIG"


class Tx(Printable):
    """交易"""

    def __init__(self, tx_in: List[Vin] = None, tx_out: List[Vout] = None):
        """
        :param tx_in: 交易输入单元的集合
        :param tx_out: 交易输出单元的集合
        """
        self.tx_in = tx_in
        self.tx_out = tx_out
        # TODO 交易费

    @property
    def is_coinbase(self) -> bool:
        """
        :return: 是否为创币交易
        """
        return len(self.tx_in) == 1 and self.tx_in[0].to_spend is None

    @classmethod
    def create_coinbase(cls, pay_to_addr: str, value: int):
        """
        创建创币交易
        :param pay_to_addr: 创币交易输出地址
        :param value: 金额
        :return: 交易
        """
        return Tx(tx_in=[Vin(to_spend=None, signature=str(os.urandom(32)), pubkey=None)],
                  tx_out=[Vout(to_addr=pay_to_addr, value=value)])

    @property
    def id(self) -> str:
        """
        :return: 交易编号
        """
        return sha256d(f"{self.tx_in}{self.tx_out}")

    @classmethod
    def from_dict(cls, dic):
        """
        从字典对象构造Tx对象
        :param dic: 字典对象
        :return: Tx对象
        """
        tx_in = []
        for vin in dic['tx_in']:
            if vin['to_spend']:
                pointer = Pointer(vin['to_spend']['tx_id'], vin['to_spend']['n'])
            else:
                pointer = None
            if vin['pubkey']:
                pubkey = bytes.fromhex(vin['pubkey'])
            else:
                pubkey = None
            tx_in.append(Vin(pointer, bytes.fromhex(vin['signature']), pubkey))
        tx_out = [Vout(vout['to_addr'], vout['value']) for vout in dic['tx_out']]
        return Tx(tx_in, tx_out)


class UTXO(Printable):
    """未使用的交易对象"""

    def __init__(self, vout: Vout, pointer: Pointer, is_coinbase: bool, unspent=True, confirmed=False):
        """
        :param vout: 封装的输出单元
        :param pointer: UTXO在区块链中的地址
        :param is_coinbase: 是否来自创币交易
        :param unspent: 是否被消费
        :param confirmed: 是否被确认
        """
        self.vout = vout
        self.pointer = pointer
        self.is_coinbase = is_coinbase
        self.unspent = unspent
        self.confirmed = confirmed

    def replace(self, unspent=True, confirmed=False):
        """
        :param unspent: 是否被消费
        :param confirmed: 是否被确认
        :return: 新的UTXO对象，用于修改UTXO状态
        """
        return UTXO(self.vout, self.pointer, self.is_coinbase, unspent, confirmed)

    @classmethod
    def from_dict(cls, dic):
        """
        从字典对象构造UTXO对象
        :param dic: 字典对象
        :return: UTXO对象
        """
        pointer = Pointer(dic['pointer']['tx_id'], dic['pointer']['n'])
        vout = Vout(dic['vout']['to_addr'], dic['vout']['value'])
        return UTXO(vout, pointer, dic['is_coinbase'], dic['unspent'], dic['confirmed'])


if __name__ == '__main__':
    pointer = Pointer(2, 3)
    vin = Vin(pointer, 2, 3)
    vout = Vout(2, 4)
    tx = Tx([vin], [vout])
    print(tx)
