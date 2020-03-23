from typing import NamedTuple, List, Union, Optional

from datatype.Transaction import Tx
from utils import BlockUtils
from utils.CryptoUtils import sha256d


class Block(NamedTuple):
    version: int
    timestamp: int
    bits: int
    nonce: int = 0
    prev_block_hash: Optional[str] = None
    merkle_root_hash: Optional[str] = None
    txs: List[Tx] = []

    def header(self, nonce: int = None, merkle_root_hash: str = None) -> str:
        if merkle_root_hash is None:
            merkle_root_hash = self.get_merkle_root()
        return "{0}{1}{2}{3}{4}{5}".format(self.version, self.prev_block_hash,
                                           self.timestamp, self.bits,
                                           merkle_root_hash, nonce or self.nonce)

    @property
    def hash(self):
        return sha256d(self.header())

    def get_merkle_root(self):
        return BlockUtils.get_merkle_root_of_txs(self.txs) if self.txs else None

    def __repr__(self):
        return "Block(hash:{0})".format(self.hash)

