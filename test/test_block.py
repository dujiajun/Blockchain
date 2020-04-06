import json
import unittest

from block import Block
from consensus import mine, calculate_target
from params import Params
from transaction import Vin, Vout, Tx
from utils.hash_utils import sha256d
from utils.json_utils import MyJSONEncoder
from utils.log import logger
from wallet import Wallet


class TestBlock(unittest.TestCase):
    def setUp(self) -> None:
        self.wallet = Wallet()
        self.wallet.generate_key()
        tx_in = [Vin(to_spend=None,
                     signature=b'I love blockchain',
                     pubkey=None)]

        tx_out = [Vout(value=Params.INITIAL_MONEY, to_addr=self.wallet.addr)]

        txs = [Tx(tx_in=tx_in, tx_out=tx_out)]
        self.block = Block(prev_hash=None,
                           timestamp=12345,
                           bits=16,
                           nonce=0,
                           txs=txs)

    def test_from_dict(self):
        block_str = json.dumps(self.block, cls=MyJSONEncoder)
        dic = json.loads(block_str)
        block = Block.from_dic(dic)
        self.assertEqual(self.block, block)

    def test_mine(self):
        nonce = mine(self.block)
        logger.debug(f"nonce={nonce}")
        self.assertLessEqual(int(sha256d(self.block.header(nonce=nonce)), 16),
                             calculate_target(self.block.bits))


if __name__ == '__main__':
    unittest.main()