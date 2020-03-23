import random
import time
from math import ceil
from typing import List, Optional

from consensus.Consensus import mine
from datatype.Block import Block
from datatype.Transaction import Tx, Vout, Vin, Pointer
from datatype.UTXO import UTXO
from peer.Peer import Peer, verify_winner_block


class Network(object):
    def __init__(self):
        self.peers: List[Peer] = []
        self.consensus_peers: List[Peer] = []
        self.current_winner : Optional[Peer] = None
        self._is_consensus_peers_chosen = False

    @property
    def nop(self):
        return len(self.peers)

    def add_peer(self):
        peer = Peer(pid=self.nop, network=self)
        self.peers.append(peer)

    def init_peers(self, number: int):
        for _ in range(number):
            self.add_peer()

    def create_genesis_block(self, value):
        tx_in = [Vin(to_spend=None,
                     signature=b'I love blockchain',
                     pubkey=None)]

        tx_out = [Vout(value=value, to_addr=peer.wallet.addrs[-1])
                  for peer in self.peers]

        txs = [Tx(tx_in=tx_in, tx_out=tx_out, locktime=0)]
        genesis_block = Block(version=0,
                              prev_block_hash=None,
                              timestamp=841124,
                              bits=0,
                              nonce=0,
                              txs=txs)

        utxos = [UTXO(vout, Pointer(tx.id, i), tx.is_coinbase, True, True)
                 for tx in txs for i, vout in enumerate(tx.tx_out)]
        for peer in self.peers:
            peer.blockchain.append(genesis_block)
            peer.utxo_set.insert(utxos)

    def make_random_transaction(self):
        k = random.randint(1, self.nop)
        for _ in range(k):
            sender = random.choice(self.peers)
            receiver = random.choice(self.peers)
            sender.create_transaction(receiver.wallet.addrs[-1],
                                      random.randint(0, 100))
            sender.broadcast_transaction()

    def choose_random_consensus_peers(self):
        n = self.nop
        # we suppose we have 20%~60% nodes are consensus node
        ub, lb = 0.6, 0.2
        k = random.randint(ceil(lb * n), ceil(ub * n))
        self.consensus_peers = random.sample(self.peers, k)
        self._is_consensus_peers_chosen = True

    def consensus(self):
        if not self._is_consensus_peers_chosen:
            self.choose_random_consensus_peers()
        n, nonce = consensus_with_fasttest_minner(self.consensus_peers)
        # self.time_spent.append(time)
        self.current_winner = self.consensus_peers[n]
        # self.winner.append(self.current_winner)

        block = self.current_winner.package_block(nonce=nonce)
        self.current_winner.receive_block(block)
        self.current_winner.broadcast_block(block)


def consensus_with_fasttest_minner(peers: List[Peer]):
    l = []
    for peer in peers:
        l.append(peer.consensus())
    return l.index(min(l)), min(l)


if __name__ == '__main__':
    net = Network()
    net.init_peers(5)
    net.create_genesis_block(100)
    net.make_random_transaction()
    net.consensus()
    print(net.peers)
