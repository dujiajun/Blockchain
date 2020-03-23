from typing import Dict, List

from datatype.Transaction import Tx, Vin
from datatype.UTXO import UTXO


class BaseMemPool(object):

    def __init__(self):
        self.mem_pool: Dict[str, Tx] = {}

    def get(self):
        pass

    def find_utxo_in_mempool(self, txin):
        pass

    def select_from_mempool(self, block, utxo_set):
        pass

    def add_txn_to_mempool(self, txn, utxo_set):
        pass


class MemPool(object):
    def __init__(self):
        super().__init__()
        self.mem_pool: Dict[str, Tx] = {}

    def get(self):
        return self.mem_pool

    def find_uxto_in_mempool(self, tx_in: Vin) -> UTXO:
        tx_id, n = tx_in.to_spend
        tx_out = self.mem_pool[tx_id].tx_out[n]
        return UTXO(tx_out, tx_in.to_spend, False)

    def add_tx_to_mempool(self, tx: Tx):
        self.mem_pool[tx.id] = tx
