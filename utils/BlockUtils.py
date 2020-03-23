from typing import List, Iterable

from datatype.Transaction import Tx
from utils.CryptoUtils import sha256d


def get_merkle_root(level: List[str]) -> str:
    while len(level) != 1:
        odd = None
        if len(level) % 2 == 1:
            odd = level.pop()
        level = [sha256d(i1 + i2) for i1, i2 in pair_node(level)]
        if odd:
            level.append(odd)
    return level[0]


def pair_node(leaves: List[str]):
    return (leaves[i:i + 2] for i in range(0, len(leaves), 2))


def get_merkle_root_of_txs(txs: Iterable[Tx]):
    return get_merkle_root([t.id for t in txs])