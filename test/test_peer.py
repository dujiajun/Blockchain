import unittest

from peer import Peer
from utils.network_utils import *


class TestPeer(unittest.TestCase):
    def setUp(self) -> None:
        self.pA = Peer()
        self.pA.generate_key()
        self.pB = Peer()
        self.pB.generate_key()
        genesis_block = create_genesis_block(self.pA.addr)
        add_genesis_block(self.pA, genesis_block)
        add_genesis_block(self.pB, genesis_block)

    def test_genesis_block(self):
        self.assertEqual(self.pA.get_balance(), Params.INITIAL_MONEY)
        self.assertEqual(self.pB.get_balance(), 0)

    def test_create_transaction(self):
        to_addr = self.pB.addr
        value = 600
        res = self.pA.create_transaction(to_addr, value)
        self.assertFalse(res)
        self.assertEqual(len(self.pA.txs), 0)
        value = 100
        self.pA.create_transaction(to_addr, value)
        self.assertEqual(len(self.pA.txs), 1)
        tx = self.pA.txs[0]
        self.assertEqual(tx.tx_out[0].to_addr, to_addr)
        self.assertEqual(tx.tx_out[0].value, value)

    def test_broadcast_txs(self):
        res = self.pA.broadcast_txs()
        self.assertFalse(res)
        self.test_create_transaction()
        tx = self.pA.txs[0]
        self.assertEqual(len(self.pA.txs), 1)
        res = self.pA.broadcast_txs()
        self.assertFalse(res)
        self.pA.add_peer('127.0.0.1')
        res = self.pA.broadcast_txs()
        self.assertTrue(res)
        self.assertEqual(len(self.pA.txs), 0)
        self.assertTrue(tx.id in self.pA.mem_pool)


if __name__ == '__main__':
    unittest.main()
