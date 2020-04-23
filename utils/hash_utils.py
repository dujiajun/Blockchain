from hashlib import sha256, new
from typing import Union

from base58 import b58encode_check


def sha256d(string: Union[str, bytes]) -> str:
    """
    SHA256双哈希
    :param string: 需要哈希的数据
    :return: 双哈希的16进制表示
    """
    if not isinstance(string, bytes):
        string = string.encode()
    return sha256(sha256(string).digest()).hexdigest()


def convert_pubkey_to_addr(pubkey: bytes) -> str:
    """
    :param pubkey: 公钥字符串
    :return: 编码后的地址
    """
    sha = sha256(pubkey).digest()
    ripe = new('ripemd160', sha).digest()
    return b58encode_check(b'\x00' + ripe).decode()


def build_message(string: str) -> bytes:
    """
    计算明文的双哈希值
    :param string: 明文
    :return: 明文的双哈希值
    """
    return sha256d(string).encode()
