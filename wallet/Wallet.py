from typing import NamedTuple, List

import ecdsa

from params.Params import Params
from utils import CryptoUtils


class Keys(NamedTuple):
    sk: ecdsa.SigningKey
    pk: ecdsa.VerifyingKey

    def __repr__(self):
        return "Key Pairs(sk:{0},pk:{0})".format(self.sk.to_string(), self.pk.to_string())


class Wallet:
    def __init__(self):
        self.keys: List[Keys] = []
        self.addrs: List[str] = []
        self.generate_keys()

    @property
    def nok(self):
        return len(self.keys)

    def generate_keys(self):
        sk = ecdsa.SigningKey.generate(curve=Params.CURVE)
        pk = sk.get_verifying_key()
        keys = Keys(sk=sk, pk=pk)
        addr = CryptoUtils.convert_pubkey_to_addr(pk.to_string())
        self.keys.append(keys)
        self.addrs.append(addr)


if __name__ == '__main__':
    wallet = Wallet()
    wallet.generate_keys()
    data = b"I Love Blockchain"
    sig = wallet.keys[0].sk.sign(data)
    print(sig)
    data2 = b"I Love Blockchain"
    try:
        res = wallet.keys[0].pk.verify(data=data2, signature=sig)
        print(res)
    except ecdsa.BadSignatureError:
        print("Verify Error")
