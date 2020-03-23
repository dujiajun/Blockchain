import time
from typing import Optional

from datatype.Block import Block
from utils.CryptoUtils import sha256d


def calculate_target(bits: int):
    return 1 << (256 - bits)


def mine(block: Block) -> Optional[Block]:
    nonce = 0
    target = calculate_target(block.bits)
    while int(sha256d(block.header(nonce)), 16) >= target:
        print(nonce)
        nonce += 1
    block = block._replace(nonce=nonce)
    return block


def get_block_reward(height, fees=0):
    ##    COIN = int(1e8)
    reward_interval = 210000
    reward = 50
    halvings = height // reward_interval

    if halvings >= 64:
        return fees

    reward >>= halvings
    return reward + fees


if __name__ == '__main__':
    b = Block(version=1, timestamp=10086, bits=20, nonce=12345, txs=[])
    print(mine(b))
