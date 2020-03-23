import random
import time
from enum import Enum
from typing import List, Optional, Dict

import ecdsa

from consensus import Consensus
from consensus.Consensus import calculate_target
from datatype.Block import Block
from datatype.Transaction import Tx, Vout, Vin, Pointer
from datatype.UTXO import UTXO
from datatype.UTXOSet import UTXOSet
from params.Params import Params
from utils import WalletUtils
from utils.CryptoUtils import sha256d, convert_pubkey_to_addr
from vm.StackMachine import StackMachine
from wallet.Wallet import Wallet


class STATE(Enum):
    TX_NONE = 0
    TX_CREATED = 1
    TX_SENT = 2


class Peer(object):

    def __init__(self, pid: int = 0, network=None):
        self.orphan_block: List[Block] = []
        self.allow_utxo_from_pool = True
        self.wallet: Wallet = Wallet()
        self.fee = 0
        self.machine = StackMachine()
        self.utxo_set = UTXOSet()
        self.mem_pool: Dict[str, Tx] = {}
        self.orphan_pool: Dict[str, Tx] = {}
        self.current_tx: Optional[Tx] = None
        self.txs: List[Tx] = []
        self.state = STATE.TX_NONE
        self.network = network
        self._delayed_tx = None
        self.blockchain: List[Block] = []
        self.candidate_block: Block = None
        self._is_block_candidate_created = False

        self._utxos_from_vins = None
        self._pointers_from_vouts = None
        self._utxos_from_vouts = None
        self._txs_removed = None

    @property
    def sk(self):
        return self.wallet.keys[-1].sk.to_string()

    @property
    def pk(self):
        return self.wallet.keys[-1].pk.to_string()

    @property
    def addr(self):
        return self.wallet.addrs[-1]

    @property
    def key_base_len(self):
        return len(self.sk)

    def get_fee(self):
        return self.fee

    def set_fee(self, fee):
        self.fee = fee

    def _get_utxos(self) -> List[UTXO]:
        return self.utxo_set.get_peer_utxos(self.wallet.addrs)

    def _get_balance(self) -> int:
        return self.utxo_set.get_peer_balance(self.wallet.addrs)

    def _get_unconfirmed_utxos(self) -> List[UTXO]:
        return self.utxo_set.get_peer_unconfirmed_utxo(self.wallet.addrs)

    def create_transaction(self, to_addr: str, value: int) -> bool:
        utxos, balance = self._get_utxos(), self._get_balance()
        utxos = sorted(utxos, key=lambda u: u.vout.value)
        fee, wallet = self.fee, self.wallet
        tx_in, tx_out = [], []
        value = value + fee
        if balance < value:
            return False
        need_to_speed, n = 0, 0
        for i, utxo in enumerate(utxos):
            need_to_speed += utxo.vout.value
            if need_to_speed >= value:
                n = i + 1
                break
        if need_to_speed > value:
            my_addr = wallet.addrs[-1]
            tx_out += [Vout(to_addr, value - fee), Vout(my_addr, need_to_speed - value)]
        else:
            tx_out += [Vout(to_addr, value - fee)]

        for utxo in utxos[:n]:
            addr = utxo.vout.to_addr
            idx = wallet.addrs.index(addr)
            sk, pk = wallet.keys[idx].sk, wallet.keys[idx].pk
            string = str(utxo.pointer) + str(pk.to_string()) + str(tx_out)
            message = sha256d(string).encode()
            signature = sk.sign(message)
            print("S:", string, "+", message, "+", signature)
            tx_in.append(Vin(utxo.pointer, signature, pk.to_string()))
        self.current_tx = Tx(tx_in, tx_out, fee=fee, locktime=0)
        self.txs.append(self.current_tx)
        self.state = STATE.TX_CREATED
        return True

    def create_coinbase(self, value) -> Tx:
        return Tx.create_coinbase(self.addr, value=value)

    def send_transaction(self) -> bool:
        if not self.txs or self.current_tx is None or self.state != STATE.TX_CREATED:
            return False
        self.utxo_set.sign_from_tx(self.current_tx)
        self.mem_pool[self.current_tx.id] = self.current_tx
        if self.allow_utxo_from_pool:
            self.utxo_set.add_utxos_from_tx(self.current_tx)
        self.state = STATE.TX_SENT
        return True

    def broadcast_transaction(self, tx: Optional[Tx] = None) -> int:
        if self.state == STATE.TX_CREATED:
            self.send_transaction()
        self.state = STATE.TX_NONE
        print("Broadcast:", self.utxo_set.utxo_set.values())
        tx = tx or self.current_tx
        if tx:
            peers = self.network.peers[:]
            peers.remove(self)
            number = broadcast_tx(peers, tx)
            self.current_tx = None
            return number
        return 0

    def verify_transaction(self, tx: Tx) -> bool:
        if tx in self.txs:
            return True
        return self.verify_tx(tx)

    def verify_tx(self, tx: Tx) -> bool:
        if not verify_tx_basic(tx):
            return False
        if verify_double_payment(tx, self.mem_pool):
            return False
        available_value = 0
        for vin in tx.tx_in:
            utxo = self.utxo_set.get(vin.to_spend)
            if not utxo:
                self.orphan_pool[tx.id] = tx
                return False
            if not self.verify_signature(vin, utxo, tx.tx_out):
                return False

            available_value += utxo.vout.value
        return True

    def verify_signature(self, vin: Vin, utxo: UTXO, tx_out: List[Vout]) -> bool:
        script, result = check_script_for_tx_in(vin, utxo, self.key_base_len)
        if not script:
            return False
        string = str(vin.to_spend) + str(vin.pubkey) + str(tx_out)
        message = sha256d(string).encode()
        print("V:", string, "+", message)
        self.machine.set_script(script, message)
        return self.machine.run()

    def add_tx_to_mem_pool(self, tx: Tx):
        self.mem_pool[tx.id] = tx
        if self.allow_utxo_from_pool:
            self.utxo_set.add_utxos_from_tx(tx)

    def fill_mem_pool(self):
        self.add_tx_to_mem_pool(self._delayed_tx)
        self._delayed_tx = None

    def check_orphan_tx_from_pool(self) -> bool:
        copy_pool = self.orphan_pool.copy()
        for tx in copy_pool.values():
            if not self.verify_tx(tx):
                return False
            self.add_tx_to_mem_pool(tx)
            del self.orphan_pool[tx.id]
        return True

    def create_candidate_block(self):

        txs = list(self.mem_pool.values())
        value = Params.FIX_BLOCK_REWARD + WalletUtils.calculate_fees(txs)
        coinbase = self.create_coinbase(value)
        txs = [coinbase] + txs

        prev_block_hash = self.blockchain[-1].hash
        bits = Params.INITIAL_DIFFICULTY_BITS
        self.candidate_block = Block(version=0,
                                     prev_block_hash=prev_block_hash,
                                     timestamp=0,
                                     bits=bits,
                                     nonce=0,
                                     txs=txs or [])

        self._is_block_candidate_created = True

    def consensus(self):
        if not self._is_block_candidate_created:
            self.create_candidate_block()
            self._is_block_candidate_created = False
        return Consensus.mine(self.candidate_block)

    def broadcast_block(self, block):
        peers = self.network.peers[:]
        peers.remove(self)
        broadcast_winner_block(peers, block)

    def package_block(self, nonce):
        block = self.candidate_block._replace(nonce=nonce)
        return block

    def get_height(self):
        return len(self.blockchain)

    def receive_block(self, block: Block):
        if not self.verify_block(block):
            return False
        return try_to_add_block(self, block)

    def verify_block(self, block):
        if self._delayed_tx:
            self.fill_mem_pool()

        if self.orphan_pool:
            self.check_orphan_tx_from_pool()

        if block == self.candidate_block:
            return True

        if not verify_winner_block(self, block):
            return False

        return True


def check_script_for_tx_in(vin: Vin, utxo: UTXO, baselen: int):
    sig_script, pubkey_script = vin.sig_script, utxo.pubkey_script
    double, fourfold = int(baselen * 2), int(baselen * 4)
    if len(sig_script) != fourfold:
        return None, False
    sig_script = [sig_script[:double], sig_script[double:]]
    try:
        pubkey_script = pubkey_script.split(' ')
    except Exception:
        return None, False
    return sig_script + pubkey_script, True


def verify_tx_basic(tx: Tx):
    if not isinstance(tx, Tx):
        return False
    if (not tx.tx_out) or (not tx.tx_in):
        return False
    return True


def verify_double_payment(tx: Tx, pool: Dict[str, Tx]):
    if tx.id in pool:
        return True
    a = {vin.to_spend for vin in tx.tx_in}
    b = {vin.to_spend for tx in pool.values() for vin in tx.tx_in}
    return a.intersection(b)


def verify_signature_for_tx_in(vin: Vin, utxo: UTXO, tx_out: List[Vout]):
    pk_str, signature = vin.pubkey, vin.signature
    to_addr = utxo.vout.to_addr
    string = str(vin.to_spend) + str(pk_str) + str(tx_out)
    message = sha256d(string).encode()
    pubkey_as_addr = convert_pubkey_to_addr(pk_str)
    verifying_key = ecdsa.VerifyingKey.from_string(pk_str, curve=Params.CURVE)
    if pubkey_as_addr != to_addr:
        return False
    try:
        print("V:", string, "+", message, "+", signature)
        verifying_key.verify(signature, message)
    except ecdsa.keys.BadSignatureError:
        return False
    return True


def verify_coinbase(tx: Tx, rewards: int):
    if not isinstance(tx, Tx):
        return False
    if not tx.is_coinbase:
        return False
    if (not len(tx.tx_out) == 1) or (tx.tx_out[0].value != rewards):
        return False
    return True


def broadcast_tx(peers: List[Peer], current_tx: Tx):
    rand, idxs, choice = random.uniform(0, 1), range(len(peers)), [-1]
    number_of_verification = 0

    if rand < Params.SLOW_PEERS_IN_NETWORK:
        choice = [random.choice(idxs)]
    if rand < Params.SLOWER_PEERS_IN_NETWORK:
        choice = random.sample(idxs, k=2)

    for i, peer in enumerate(peers):
        if peer._delayed_tx:
            dice = random.uniform(0, 1)
            if dice > Params.SLOW_PEERS_IN_NETWORK:
                peer.fill_mem_pool()

        if peer.verify_transaction(current_tx):
            if (i in choice) and (not peer._delayed_tx):
                peer._delayed_tx = current_tx
                continue

            peer.add_tx_to_mem_pool(current_tx)
            number_of_verification += 1

        if peer.orphan_pool:
            peer.check_orphan_tx_from_pool()

    return number_of_verification


def broadcast_winner_block(peers, block):
    number_of_verification = 0
    for peer in peers:
        if peer.verify_block(block):
            try_to_add_block(peer, block)
            number_of_verification += 1

    return number_of_verification


def try_to_add_block(peer: Peer, block: Block):
    prev_hash = block.prev_block_hash
    height = None
    for i, block in enumerate(peer.blockchain):
        if block.hash == prev_hash:
            height = i + 1
            break
    if not height:
        peer.orphan_block.append(block)
        return False

    if height == peer.get_height():
        peer.blockchain.append(block)
        recieve_new_prev_hash_block(peer, block.txs)
        return True

    elif height == peer.get_height() - 1:
        b1, b2 = peer.blockchain[-1], block
        a, b = int(b1.hash, 16), int(b2.hash, 16)
        if a < b:
            return False
        else:
            peer.blockchain.pop()
            peer.blockchain.append(block)
            recieve_exist_prev_hash_block(peer, block.txs)
    else:
        return False


def recieve_new_prev_hash_block(peer: Peer, txs: List[Tx]):
    utxo_set, pool = peer.utxo_set, peer.mem_pool
    allow_utxo_from_pool = peer.allow_utxo_from_pool
    peer._utxos_from_vins = peer.utxo_set.remove_from_txs(txs)
    peer._pointers_from_vouts, peer._utxos_from_vouts = peer.utxo_set.confirm_from_txs(txs, allow_utxo_from_pool)
    peer._txs_removed = remove_txs_from_pool(pool, txs)


def remove_txs_from_pool(pool: Dict[str, Tx], txs: List[Tx]):
    n_txs = {}
    for tx in txs:
        if tx.id in pool:
            n_txs[tx.id] = tx
            del pool[tx.id]
    return n_txs


def recieve_exist_prev_hash_block(peer: Peer, txs: List[Tx]):
    roll_back(peer)
    recieve_new_prev_hash_block(peer, txs)


def roll_back(peer: Peer):
    peer.mem_pool.update(peer._txs_removed)
    peer.utxo_set.insert(peer._utxos_from_vins)
    peer.utxo_set.remove(peer._pointers_from_vouts)
    peer.utxo_set.insert(peer._utxos_from_vouts)
    peer._utxos_from_vins = []
    peer._pointers_from_vouts = []
    peer._utxos_from_vouts = []
    peer._txs_removed = {}


def verify_winner_block(peer: Peer, block: Block):
    if not isinstance(block, Block):
        return False
    if int(block.hash, 16) > calculate_target(block.bits):
        return False
    txs = block.txs
    if not isinstance(txs, list):
        return False
    if len(txs) < 2:
        return False
    print(1)
    block_txs = txs[1:]
    rewards = Params.FIX_BLOCK_REWARD + WalletUtils.calculate_fees(block_txs)
    if not verify_coinbase(block.txs[0], rewards):
        return False

    if double_payment_in_block_txs(block_txs):
        return False

    for tx in block_txs:
        if not peer.verify_tx(tx):
            return False
    return True


def double_payment_in_block_txs(txs: List[Tx]):
    a = {vin.to_spend for tx in txs for vin in tx.tx_in}
    b = [vin.to_spend for tx in txs for vin in tx.tx_in]
    return len(a) != len(b)


if __name__ == '__main__':
    zhangsan = Peer()
    lisi = Peer()
    peers = [zhangsan, lisi]
    value = 200
    tx_in = [Vin(to_spend=None,
                 signature=b'I love blockchain',
                 pubkey=None)]
    tx_out = [Vout(value=value, to_addr=peer.wallet.addrs[-1])
              for peer in peers]
    txs = [Tx(tx_in=tx_in, tx_out=tx_out, locktime=0)]
    utxos = [UTXO(vout, Pointer(tx.id, i), tx.is_coinbase, True, True)
             for tx in txs for i, vout in enumerate(tx.tx_out)]
    for peer in peers:
        peer.utxo_set.insert(utxos)
    res = zhangsan.create_transaction(lisi.addr, 100)
    print(res)
    base = Tx.create_coinbase(1, 20)
    print(base)
