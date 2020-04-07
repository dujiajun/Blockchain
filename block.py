from time import time

from merkle_tree import get_merkle_root_of_txs
from params import Params
from transaction import Tx
from utils.hash_utils import sha256d
from utils.printable import Printable


class Block(Printable):
    """
    区块
    """

    def __init__(self, timestamp=None, prev_hash=None, nonce=0,
                 bits=Params.DIFFICULTY_BITS, txs=None):
        """
        :param timestamp: 时戳
        :param prev_hash: 区块链中前一区块的哈希值
        :param nonce: 工作量证明使用到的随机数
        :param txs: 区块中包含的交易列表
        :type txs: list[Tx]
        """
        self.version = 0
        self.timestamp = timestamp or int(time())
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.bits = bits
        self.txs = txs
        self.merkle_root = get_merkle_root_of_txs(self.txs) if self.txs else None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.header() != other.header():
                return False
            if self.txs is None and other.txs is None:
                return True
            if isinstance(self.txs, list) and isinstance(other.txs, list):
                if len(self.txs) != len(other.txs):
                    return False
                for i, tx in enumerate(self.txs):
                    if tx.id != other.txs[i].id:
                        return False
                return True
            else:
                return False
        return False

    def header(self, nonce=None) -> str:
        """
        :return: 区块头
        :rtype: str
        """
        return f"{self.version}{self.timestamp}{self.prev_hash}{nonce or self.nonce}{self.bits}{self.merkle_root}"

    @property
    def hash(self) -> str:
        """
        :return: 区块头的哈希值
        :rtype: str
        """
        return sha256d(self.header())

    def replace(self, nonce=None):
        """
        仅替换区块中的nonce，构造新的区块
        :param nonce:
        :return: 新区块
        """
        return Block(self.timestamp, self.prev_hash, nonce or self.nonce, self.bits, self.txs)

    @classmethod
    def from_dict(cls, dic):
        if dic is None or len(dic) == 0:
            return None
        txs = [Tx.from_dict(dic) for dic in dic['txs']]
        return Block(dic['timestamp'], dic['prev_hash'], dic['nonce'], dic['bits'], txs)
