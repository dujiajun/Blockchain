from block import Block
from params import Params
from transaction import Vin, Vout, Tx
from utils.transaction_utils import add_utxos_to_set, find_utxos_from_block


def create_genesis_block(peer):
    """
    初始化创世区块
    """
    tx_in = [Vin(to_spend=None,
                 signature=b'I love blockchain',
                 pubkey=None)]

    tx_out = [Vout(value=Params.INITIAL_MONEY, to_addr=peer.addr)]

    txs = [Tx(tx_in=tx_in, tx_out=tx_out)]
    genesis_block = Block(prev_hash=None,
                          timestamp=12345,
                          bits=0,
                          nonce=0,
                          txs=txs)
    peer.chain.append(genesis_block)
    utxos = find_utxos_from_block(txs)
    add_utxos_to_set(peer.utxo_set, utxos)
