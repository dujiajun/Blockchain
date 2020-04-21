from blockchain.block import Block
from blockchain.consensus import mine
from blockchain.params import Params
from blockchain.transaction import Vin, Vout, Tx
from utils.transaction_utils import add_utxos_to_set, find_utxos_from_block


def create_genesis_block(addr, value=Params.INITIAL_MONEY) -> Block:
    """
    初始化创世区块
    """
    tx_in = [Vin(to_spend=None,
                 signature=b'I love blockchain',
                 pubkey=None)]

    tx_out = [Vout(value=value, to_addr=addr)]

    txs = [Tx(tx_in=tx_in, tx_out=tx_out)]
    block = Block(prev_hash=None,
                  timestamp=12345,
                  bits=18,
                  nonce=0,
                  txs=txs)
    nonce = mine(block)
    return block.replace(nonce)


def add_genesis_block(peer, genesis_block):
    peer.chain.append(genesis_block)
    utxos = find_utxos_from_block(genesis_block.txs)
    add_utxos_to_set(peer.utxo_set, utxos)
