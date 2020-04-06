import unittest

from peer import Peer, Tx
from transaction import Vin, Vout
from utils.transaction_utils import *


class TestTransactionUtils(unittest.TestCase):
    def setUp(self) -> None:
        self.peer = Peer()
        self.peer.generate_key()
        self.tx = Tx.create_coinbase(self.peer.addr, 100)

    def test_add_tx_to_mem_pool(self):
        self.assertNotIn(self.tx.id, self.peer.mem_pool)
        add_tx_to_mem_pool(self.peer, self.tx)
        self.assertIn(self.tx.id, self.peer.mem_pool)

    def test_add_utxos_to_set(self):
        utxo_set = {}
        utxos = find_utxos_from_tx(self.tx)
        add_utxos_to_set(utxo_set, utxos)
        for utxo in utxos:
            self.assertIn(utxo.pointer, utxo_set)
            self.assertEqual(utxo_set[utxo.pointer], utxo)

    def test_add_utxos_from_tx_to_set(self):
        self.assertTrue(len(self.peer.utxo_set) == 0)
        add_utxos_from_tx_to_set(self.peer.utxo_set, self.tx)
        utxos = find_utxos_from_tx(self.tx)
        for utxo in utxos:
            self.assertEqual(utxo, self.peer.utxo_set[utxo.pointer])
        for utxo in self.peer.utxo_set.values():
            self.assertTrue(utxo.unspent)
            self.assertFalse(utxo.confirmed)

    def test_find_utxos_from_tx(self):
        utxos = find_utxos_from_tx(self.tx)
        for utxo in utxos:
            self.assertTrue(isinstance(utxo, UTXO))
            self.assertTrue(utxo.unspent)
            self.assertFalse(utxo.confirmed)

    def test_find_utxos_from_block(self):
        utxos = find_utxos_from_block([self.tx])
        for utxo in utxos:
            self.assertTrue(isinstance(utxo, UTXO))
            self.assertTrue(utxo.unspent)
            self.assertTrue(utxo.confirmed)

    def test_add_utxos_from_block_to_set(self):
        self.assertTrue(len(self.peer.utxo_set) == 0)
        add_utxos_from_block_to_set(self.peer.utxo_set, [self.tx])
        utxos = find_utxos_from_block([self.tx])
        for utxo in utxos:
            self.assertEqual(utxo, self.peer.utxo_set[utxo.pointer])
        for utxo in self.peer.utxo_set.values():
            self.assertTrue(utxo.unspent)
            self.assertTrue(utxo.confirmed)

    def test_remove_utxos_from_set(self):
        add_utxos_from_tx_to_set(self.peer.utxo_set, self.tx)
        utxos = find_utxos_from_tx(self.tx)
        pointers = [utxo.pointer for utxo in utxos]
        deleted = remove_utxos_from_set(self.peer.utxo_set, pointers)
        for pointer in pointers:
            self.assertIsNone(self.peer.utxo_set.get(pointer, None))
        self.assertListEqual(deleted, utxos)

    def test_remove_spent_utxo_from_txs(self):
        utxo_set = {}
        utxos = find_utxos_from_tx(self.tx)
        add_utxos_to_set(utxo_set, utxos)
        self.assertTrue(len(utxo_set) > 0)
        tx_in = [Vin(to_spend=utxo.pointer, signature=None, pubkey=None) for utxo in utxos]
        tx = Tx(tx_in=tx_in, tx_out=None)
        removed = remove_spent_utxo_from_txs(utxo_set, [tx])
        self.assertTrue(len(utxo_set) == 0)
        self.assertListEqual(utxos, removed)

    def test_remove_txs_from_pool(self):
        add_tx_to_mem_pool(self.peer, self.tx)
        self.assertTrue(len(self.peer.mem_pool) > 0)
        txs = remove_txs_from_pool(self.peer.mem_pool, [self.tx])
        self.assertTrue(len(self.peer.mem_pool) == 0)
        self.assertListEqual([self.tx], list(txs.values()))

    def test_confirm_utxos_from_txs(self):
        utxo_set = {}
        tx = Tx(tx_in=[Vin(to_spend=Pointer(self.tx.id, 0), signature=None, pubkey=None)],
                tx_out=[Vout(self.peer.addr, 100)])
        confirm_utxos_from_txs(utxo_set, [tx], True)
        utxos = find_utxos_from_tx(tx)
        for utxo in utxos:
            self.assertTrue(utxo_set[utxo.pointer].unspent)
            self.assertTrue(utxo_set[utxo.pointer].confirmed)

    def test_sign_utxo_from_tx(self):
        utxo_set = {}
        utxos = find_utxos_from_tx(self.tx)
        add_utxos_to_set(utxo_set, utxos)
        tx = Tx(tx_in=[Vin(to_spend=Pointer(self.tx.id, 0), signature=None, pubkey=None)],
                tx_out=[Vout(self.peer.addr, 100)])
        utxos = find_utxos_from_tx(tx)
        for utxo in utxos:
            self.assertFalse(utxo.confirmed)
            self.assertTrue(utxo.unspent)
        add_utxos_to_set(utxo_set, utxos)
        sign_utxo_from_tx(utxo_set, tx)
        self.assertFalse(utxo_set[tx.tx_in[0].to_spend].unspent)
        self.assertFalse(utxo_set[tx.tx_in[0].to_spend].confirmed)


if __name__ == '__main__':
    unittest.main()
