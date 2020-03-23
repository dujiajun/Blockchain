from typing import Dict, List

from datatype.Transaction import Pointer, Tx
from datatype.UTXO import UTXO


class BaseUTXOSet(object):

    def __init__(self):
        self.utxo_set: Dict[Pointer, UTXO] = {}

    def get(self):
        pass

    def add_to_utxo(self, txout, tx, idx, is_coinbase, height):
        pass

    def remove_from_utxo(self, txid, txout_idx):
        pass

    def find_utxo_in_list(self, txin, txns):
        pass

    def validate_txn(self, txn, mempool, as_coinbase, siblings_in_block, allow_utxo_from_mempool):
        pass


class UTXOSet(object):
    def __init__(self):
        super().__init__()
        self.utxo_set: Dict[Pointer, UTXO] = {}

    def get(self, pointer: Pointer) -> UTXO:
        return self.utxo_set[pointer]

    def get_utxos(self) -> List[UTXO]:
        return [utxo for utxo in self.utxo_set.values()]

    def insert(self, utxos):
        if isinstance(utxos, dict):
            utxos = utxos.values()
        for utxo in utxos:
            self.utxo_set[utxo.pointer] = utxo

    def remove(self, pointer: Pointer):
        if isinstance(pointer, list):
            for p in pointer:
                self.utxo_set.pop(p)
        else:
            self.utxo_set.pop(pointer)

    def confirm(self, pointer: Pointer):
        utxo = self.utxo_set[pointer].replace(confirmed=True)
        self.utxo_set[pointer] = utxo

    def sign_from_tx(self, tx: Tx):
        for vin in tx.tx_in:
            pointer = vin.to_spend
            utxo = self.utxo_set[pointer].replace(unspent=False)
            self.utxo_set[pointer] = utxo

    def get_peer_utxos(self, addrs: List[str]):
        return [utxo for utxo in self.utxo_set.values() if (utxo.vout.to_addr in addrs) and utxo.unspent]

    def get_peer_unconfirmed_utxo(self, addrs: List[str]) -> List[UTXO]:
        utxos = self.get_peer_utxos(addrs)
        return [utxo for utxo in utxos if not utxo.confirmed]

    def get_peer_balance(self, addrs: List[str]):
        utxos = self.get_peer_utxos(addrs)
        return sum(utxo.vout.value for utxo in utxos)

    def add_utxos_from_tx(self, tx: Tx):
        utxos = [UTXO(tx_out, Pointer(tx.id, i), tx.is_coinbase)
                 for i, tx_out in enumerate(tx.tx_out)]
        self.insert(utxos)

    def remove_from_txs(self, txs: List[Tx]):
        pointers = [vin.to_spend for tx in txs for vin in tx.tx_in]
        for pointer in pointers:
            self.remove(pointer)

    def confirm_from_txs(self, txs: List[Tx], allow_utxo_from_pool):
        if allow_utxo_from_pool:
            utxos = find_utxos_from_txs(txs[1:])
            self.add_utxo_from_block(txs)
            pointers = find_vout_pointer_from_txs(txs)
            return pointers, utxos
        else:
            utxos = find_utxos_from_block(txs)
            pointers = find_vout_pointer_from_txs(txs)
            self.insert(utxos)
            return pointers, []

    def add_utxo_from_block(self, txs: List[Tx]):
        utxos = find_utxos_from_block(txs)
        self.insert(utxos)


def find_utxos_from_txs(txs: List[Tx]):
    return [UTXO(vout, Pointer(tx.id, i), tx.is_coinbase)
            for tx in txs for i, vout in enumerate(tx.tx_out)]


def find_utxos_from_block(txs: List[Tx]):
    return [UTXO(vout, Pointer(tx.id, i), tx.is_coinbase, True, True)
            for tx in txs for i, vout in enumerate(tx.tx_out)]


def find_utxos_from_tx(tx: Tx):
    return [UTXO(vout, Pointer(tx.id, i), tx.is_coinbase)
            for i, vout in enumerate(tx.tx_out)]


def find_vout_pointer_from_txs(txs: List[Tx]):
    return [Pointer(tx.id, i) for tx in txs for i, vout in enumerate(tx.tx_out)]


def find_vin_pointer_from_txs(txs: List[Tx]):
    return [vin.to_spend for tx in txs for vin in tx.tx_in]
