import os
import random
import time

import ecdsa
import matplotlib.pyplot as plt
import numpy as np

from blockchain.block import Block
from blockchain.consensus import mine
from blockchain.params import Params
from blockchain.transaction import Vin, Vout, Tx
# plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
# plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
from peer import Peer
from utils.hash_utils import sha256d
from utils.network_utils import create_genesis_block, add_genesis_block


def draw_ecc():
    def draw_ecc_with_params(a: int, b: int, xlim: int, ylim: int):
        y, x = np.ogrid[-ylim:ylim:100j, -xlim:xlim:100j]
        fig, ax = plt.subplots()

        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')

        ax.xaxis.set_ticks_position('bottom')
        ax.yaxis.set_ticks_position('left')

        ax.spines['bottom'].set_position(('data', 0))
        ax.spines['left'].set_position(('data', 0))

        ax.contour(x.ravel(), y.ravel(), pow(y, 2) - pow(x, 3) - x * a - b, [0])

        plt.savefig(f'plot/ecc_{a}_{b}.pdf', dpi=600)
        plt.show()

    # draw_ecc_with_params(-1, 0, 2, 2)
    # draw_ecc_with_params(0, 64, 8, 20)
    draw_ecc_with_params(0, 7, 8, 10)


def draw_consensus_speed():
    def consensus_with_bits(bits: int):
        tx_in = [Vin(to_spend=None,
                     signature=b'Shanghai Jiao Tong University',
                     pubkey=None)]

        tx_out = [Vout(value=0, to_addr=0)]

        txs = [Tx(tx_in=tx_in, tx_out=tx_out)]
        block = Block(prev_hash=None,
                      timestamp=time.time(),
                      bits=bits,
                      nonce=0,
                      txs=txs)
        begin = time.time()
        mine(block)
        end = time.time()
        print(bits, end - begin)
        return end - begin

    def calc_average_time(x: int):
        y = np.zeros(10)
        for i in range(10):
            y[i] = consensus_with_bits(x)
        return np.average(y)

    x = range(1, 25)
    y = [calc_average_time(i) for i in x]

    plt.plot(x, y)
    plt.xticks(x)
    plt.xlabel('difficulty (bits)')
    plt.ylabel('consensus time (s)')
    plt.savefig('plot/pow_time.pdf', dpi=600)
    plt.show()


def calc_hash_time(x: int, buf_size: int = 1024):
    message = os.urandom(buf_size)
    begin = time.time()
    for i in range(x):
        sha256d(message)
    end = time.time()
    return end - begin


def calc_ecdsa_time(x: int, buf_size: int = 1024):
    sk = ecdsa.SigningKey.generate(curve=Params.CURVE)
    pk = sk.get_verifying_key()
    message = os.urandom(buf_size)

    begin = time.time()
    for i in range(x):
        sk.sign(message)
    end = time.time()
    sign_time = end - begin

    sig = sk.sign(message)

    begin = time.time()
    for i in range(x):
        pk.verify(sig, message)
    end = time.time()
    verify_time = end - begin
    return sign_time, verify_time


def draw_hash_sign_time():
    times = 200
    y = np.zeros(2)
    hash_time = calc_hash_time(times)
    print(times / hash_time, hash_time / times)
    y[0], y[1] = calc_ecdsa_time(times)
    print(times / y, y / times)
    x_label = ['Sign', 'Verify']
    plt.bar(x_label, times / y)
    plt.show()


def calc_create_and_verify_time():
    pA = Peer()
    pA.generate_key()
    genesis_block = create_genesis_block(pA.addr)
    add_genesis_block(pA, genesis_block)
    pA.allow_utxo_from_pool = True

    tx_cnt = 50
    to_addr = pA.addr
    create_time = 0.0
    verify_time = 0.0

    for _ in range(tx_cnt):
        value = random.randint(1, 10)
        begin = time.time()
        pA.create_transaction(to_addr, value)
        create_time += time.time() - begin
        begin = time.time()
        pA.receive_transaction(pA.txs[-1])
        verify_time += time.time() - begin

    print(create_time / tx_cnt, tx_cnt / create_time, verify_time / tx_cnt, tx_cnt / verify_time)


draw_ecc()
