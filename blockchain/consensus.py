from utils.hash_utils import sha256d


def calculate_target(bits) -> int:
    """
    :param bits: 位数
    :return: 目标值
    """
    return 1 << (256 - bits)


def mine(block) -> int:
    """
    挖矿
    :param block: 最开始的情况
    :return: nonce值
    """
    nonce = block.nonce
    target = calculate_target(block.bits)
    while int(sha256d(block.header(nonce)), 16) >= target:
        nonce += 1
    return nonce
