from params import Params
from utils.hash_utils import sha256d
from utils.printable import Printable


class Block(Printable):
    """
    区块
    """

    def __init__(self, timestamp=None, prev_hash=None, nonce=0,
                 bits=Params.DIFFICULTY_BITS, merkle_root=None,
                 txs=None):
        """
        :param timestamp: 时戳
        :param prev_hash: 区块链中前一区块的哈希值
        :param nonce: 工作量证明使用到的随机数
        :param txs: 区块中包含的交易列表
        :param merkle_root: 梅克尔树根哈希值
        :type txs: list[Tx]
        """
        self.version = 0
        self.timestamp = timestamp or 0
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.bits = bits
        self.merkle_root = merkle_root
        self.txs = txs

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
        return Block(self.timestamp, self.prev_hash, nonce or self.nonce, self.bits, self.merkle_root, self.txs)
