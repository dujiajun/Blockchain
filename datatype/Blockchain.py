from typing import List

from datatype.Block import Block


class Blockchain(object):
    def __init__(self):
        self.chain: List[Block] = []

    @property
    def height(self):
        return len(self.chain)

