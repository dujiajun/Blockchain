import os
from typing import NamedTuple, List, Union

from utils.CryptoUtils import sha256d


class Pointer(NamedTuple):
    tx_id: str
    n: int

    def __repr__(self):
        return "Pointer(tx_id:{0}, n:{1})".format(self.tx_id, self.n)


class Vin(NamedTuple):
    to_spend: Pointer
    signature: bytes
    pubkey: bytes

    @property
    def sig_script(self) -> bytes:
        return self.signature + self.pubkey

    def __repr__(self):
        return "Vin(to_spend:{0}, signature:{1}, pubkey:{2})".format(self.to_spend, self.signature, self.pubkey)


class Vout(NamedTuple):
    to_addr: str
    value: int

    @property
    def pubkey_script(self) -> str:
        return "OP_DUP OP_ADDR {0} OP_EQ OP_CHECKSIG".format(self.to_addr)

    def __repr__(self):
        return "Vout(to_addr:{0}, value:{1})".format(self.to_addr, self.value)


class Tx(NamedTuple):
    tx_in: List[Vin]
    tx_out: List[Vout]
    fee: int = 0
    locktime: int = 0

    @property
    def is_coinbase(self) -> bool:
        return len(self.tx_in) == 1 and self.tx_in[0].to_spend is None

    @classmethod
    def create_coinbase(cls, pay_to_addr, value):
        return Tx(tx_in=[Vin(to_spend=None, signature=str(os.urandom(32)), pubkey=None)],
                  tx_out=[Vout(to_addr=pay_to_addr, value=value)])

    @property
    def id(self):
        return sha256d(self.to_string())

    def to_string(self) -> str:
        return "{0}{1}{2}".format(self.tx_in, self.tx_out, self.locktime)

    def __repr__(self):
        return "Tx(id:{0})".format(self.id)


if __name__ == "__main__":
    base = Tx.create_coinbase(1, 20)
    print(base)
