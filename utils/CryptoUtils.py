import hashlib
from hashlib import sha256
from typing import Union

from base58 import b58encode_check


def sha256d(string: Union[str, bytes]) -> str:
    if not isinstance(string, bytes):
        string = string.encode()
    return sha256(sha256(string).digest()).hexdigest()


def convert_pubkey_to_addr(pubkey_str: bytes):
    sha = sha256(pubkey_str).digest()
    ripe = hashlib.new('ripemd160', sha).digest()
    return b58encode_check(b'\x00' + ripe).decode()


if __name__ == "__main__":
    print(sha256d(input()))
