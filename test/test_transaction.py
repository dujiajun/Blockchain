import json
import unittest

from transaction import *
from utils.json_utils import MyJSONEncoder


class TestTransaction(unittest.TestCase):
    def setUp(self) -> None:
        self.addr = "123456"
        self.value = 100
        self.tx = Tx.create_coinbase(self.addr, self.value)
        self.pointer = Pointer(self.tx.id, 0)

    def test_pointer_eq(self):
        self.assertEqual(self.pointer, Pointer(self.tx.id, 0))
        self.assertNotEqual(self.pointer, Pointer(self.tx.id, 1))
        self.assertNotEqual(self.pointer, 1)
        self.assertNotEqual(self.pointer, Pointer("1234", 0))

    def test_tx_eq(self):
        self.assertEqual(Tx(), Tx())
        self.assertNotEqual(self.tx, Tx.create_coinbase(self.addr, self.value))

    def test_tx_coinbase(self):
        self.assertTrue(self.tx.is_coinbase)
        self.assertFalse(Tx([], []).is_coinbase)

    def test_tx_from_dict(self):
        tx_str = json.dumps(self.tx, cls=MyJSONEncoder)
        dic = json.loads(tx_str)
        tx = Tx.from_dict(dic)
        self.assertEqual(self.tx, tx)

    def test_utxo_replace(self):
        utxo = UTXO(Vout(self.addr, self.value), self.pointer, self.tx.is_coinbase)
        utxo_replaced = utxo.replace(unspent=False)
        self.assertFalse(utxo_replaced.unspent)

    def test_utxo_from_dic(self):
        utxo = UTXO(Vout(self.addr, self.value), self.pointer, self.tx.is_coinbase)
        utxo_str = json.dumps(utxo, cls=MyJSONEncoder)
        dic = json.loads(utxo_str)
        self.assertEqual(utxo, UTXO.from_dict(dic))


if __name__ == '__main__':
    unittest.main()
