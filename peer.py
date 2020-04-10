import json
import traceback
from typing import Dict

import requests

from consensus import mine
from transaction import Vout, Vin
from utils.json_utils import MyJSONEncoder
from utils.transaction_utils import *
from utils.verify_utils import *
from wallet import Wallet


class Peer:
    """区块链的参与者对象"""

    def __init__(self):
        self.chain = []
        self.txs = []  # 离线交易
        self.peer_nodes = set()
        self.utxo_set: Dict[Pointer, UTXO] = {}
        self.mem_pool: Dict[str, Tx] = {}
        self.orphan_pool: Dict[str, Tx] = {}
        self.wallet = Wallet()
        self.allow_utxo_from_pool = True
        self.orphan_block = []
        self.candidate_block = None
        self.port = 5000
        self.fee = Params.DEFAULT_FEE
        self.__utxos_from_vins = []
        self.__utxos_from_vouts = []
        self.__pointers_from_vouts = []
        self.__txs_removed = {}

    @property
    def addr(self):
        """
        :return: 钱包地址
        """
        return self.wallet.addr if self.wallet.addr else None

    @property
    def pk(self):
        """
        :return:公钥
        """
        return self.wallet.pk.to_string() if self.wallet.pk else None

    @property
    def sk(self):
        """
        :return: 私钥
        """
        return self.wallet.sk.to_string() if self.wallet.sk else None

    @property
    def key_base_len(self):
        return len(self.sk)

    def generate_key(self):
        """
        产生密钥对
        """
        self.wallet.generate_key()

    def get_utxos(self):
        """
        :return: 自己未消费的UTXO列表
        """
        return [utxo for utxo in self.utxo_set.values()
                if utxo.vout.to_addr == self.addr and utxo.unspent]

    def get_balance(self):
        """
        :return: 自身余额
        """
        utxos = self.get_utxos()
        return sum([utxo.vout.value for utxo in utxos])

    def create_transaction(self, to_addr, value):
        """
        创建交易
        :param to_addr: 交易目标
        :param value: 交易金额
        :return: 是否创建成功
        """
        utxos, balance = self.get_utxos(), self.get_balance()
        utxos = sorted(utxos, key=lambda u: u.vout.value)  # 按金额从小到大排序
        if balance < value:  # 余额不足
            logger.info("创建交易失败：余额不足！")
            return False
        tx_in, tx_out = [], []
        need_to_spend = 0
        n = 0  # 前n个UTXO
        for i, utxo in enumerate(utxos):
            need_to_spend += utxo.vout.value
            if need_to_spend >= value:
                n = i + 1
                break
        if need_to_spend > value:  # 需要找零
            tx_out.append(Vout(to_addr=to_addr, value=value - self.fee))
            tx_out.append(Vout(to_addr=self.addr, value=need_to_spend - value))
        else:
            tx_out.append(Vout(to_addr=to_addr, value=value - self.fee))
        for utxo in utxos[:n]:
            message = self.wallet.create_signature(self.pk, utxo.pointer, tx_out)
            signature = self.wallet.sign(message)
            tx_in.append(Vin(to_spend=utxo.pointer, signature=signature, pubkey=self.pk))
            # self.utxo_set[utxo.pointer] = utxo.replace(unspent=False)
        tx = Tx(tx_in=tx_in, tx_out=tx_out, fee=self.fee)
        logger.info(f"创建交易：{tx}")
        self.txs.append(tx)
        return True

    def broadcast_transaction(self, tx):
        """
        广播单条交易
        :param tx: 交易
        """
        add_tx_to_mem_pool(self, tx)  # 离线交易进入交易池
        payload = {'tx': str(tx)}

        for node in self.peer_nodes:
            url = f"http://{node}/broadcast-transaction"
            logger.info(f"广播交易：向{node}广播交易")
            requests.post(url, payload)

    def receive_transaction(self, tx):
        """
        接收交易并将其放入交易池中
        :param tx: 交易
        :return: 是否成功
        """
        if isinstance(tx, Tx) and (tx.id not in self.mem_pool):
            if verify_tx(self, tx, self.mem_pool):
                logger.info(f"接收交易：验证交易成功：{tx}")
                sign_utxo_from_tx(self.utxo_set, tx)
                add_tx_to_mem_pool(self, tx)
                return True
        logger.info(f"接收交易：验证交易失败：{tx}")
        return False

    def broadcast_txs(self):
        """广播所有离线交易"""
        # 无需广播
        if len(self.txs) == 0:
            logger.info("广播交易：离线交易为空")
            return False
        if len(self.peer_nodes) == 0:
            logger.info("广播交易：邻居为空")
            return False

        # 离线交易进入交易池
        for tx in self.txs:
            sign_utxo_from_tx(self.utxo_set, tx)
            add_tx_to_mem_pool(self, tx)

        # 广播时让对方发现自己端口号（request可获取IP地址）
        payload = {'port': self.port, 'txs': json.dumps(self.txs, cls=MyJSONEncoder)}
        for node in self.peer_nodes:
            url = f"http://{node}/receive-transaction"
            logger.info(f"广播交易：向{node}广播离线交易")
            try:
                requests.post(url, payload)
            except Exception:
                traceback.print_exc(limit=1)
        self.txs.clear()
        return True

    def load_genesis_block(self, filename='genesis_block.txt'):
        """加载创世区块"""
        with open(filename, mode='r') as f:
            line = f.readlines()[0]
            block_dic = json.loads(line)
            block = Block.from_dict(block_dic)
            self.chain = [block]
            utxos = find_utxos_from_block(block.txs)
            add_utxos_to_set(self.utxo_set, utxos)

    def create_candidate_block(self):
        """
        构造候选区块
        :return: 区块
        """

        prev_hash = self.chain[-1].hash
        txs = list(self.mem_pool.values())

        value = Params.MINING_REWARDS + calculate_fees(txs)
        coinbase = Tx.create_coinbase(self.addr, value)
        txs = [coinbase] + txs
        self.candidate_block = Block(prev_hash=prev_hash, nonce=0,
                                     bits=Params.DIFFICULTY_BITS, txs=txs)
        logger.info(f"创建候选区块：{self.candidate_block}")

    def consensus(self):
        """
        进行共识
        :return: 修改nonce后的区块
        """
        if not self.candidate_block:
            self.create_candidate_block()
        block = self.candidate_block
        logger.info("共识：开始挖矿！")
        nonce = mine(block)
        logger.info(f"共识：挖矿结束，nonce={nonce}")
        self.candidate_block = block.replace(nonce=nonce)

    def broadcast_block(self):
        """
        广播区块
        """
        # 无需广播
        if self.candidate_block is None:
            logger.info("广播区块：未创建候选区块")
            return False
        payload = {'port': self.port, 'block': json.dumps(self.candidate_block, cls=MyJSONEncoder)}
        for node in self.peer_nodes:
            url = f"http://{node}/receive-block"
            logger.info(f"广播区块：向{node}广播区块")
            requests.post(url, payload)
        self.receive_block(self.candidate_block)
        self.candidate_block = None
        return True

    def receive_block(self, block):
        """
        接收区块并验证和加入链中
        :param block: 区块
        :return: 是否成功
        """
        if self.orphan_pool:
            verify_tx_in_orphan_pool(self)

        if not verify_block(self, block):
            return False

        prev_hash = block.prev_hash
        height = locate_block_by_hash(self.chain, prev_hash)
        if height == -1:  # 孤儿区块
            logger.debug("区块为孤儿区块")
            self.orphan_block.append(block)
            return False
        if height == len(self.chain):  # 父区块在链尾
            logger.info("添加区块到区块链末尾成功")
            self.chain.append(block)
            self.update_after_receive_block(block.txs)  # 更新UTXO_SET和交易池
            return True
        elif height == len(self.chain) - 1:  # 父区块在链尾前一个
            a = int(self.chain[-1].hash, 16)
            b = int(block.hash, 16)
            if a < b:  # 比较区块的哈希值
                return False
            else:
                self.chain.pop()
                self.chain.append(block)
                self.roll_back()
                self.update_after_receive_block(block.txs)
                return True
        else:
            return False

    def update_after_receive_block(self, txs):
        """
        在接收区块后更新UTXO_SET和交易池
        :param txs: 交易
        """
        utxo_set, pool = self.utxo_set, self.mem_pool
        # 将交易使用过的UTXO从UTXO_SET移除
        self.__utxos_from_vins = remove_spent_utxo_from_txs(utxo_set, txs)
        # 将区块交易所有Vout封装成已确认的UTXO添加到UTXO_SET中，并备份
        self.__pointers_from_vouts, self.__utxos_from_vouts = \
            confirm_utxos_from_txs(utxo_set, txs, self.allow_utxo_from_pool)
        # 将区块交易从交易池中移除，并备份
        self.__txs_removed = remove_txs_from_pool(pool, txs)

    def roll_back(self):
        """
        分叉后回滚
        """
        self.mem_pool.update(self.__txs_removed)
        add_utxos_to_set(self.utxo_set, self.__utxos_from_vins)
        remove_utxos_from_set(self.utxo_set, self.__pointers_from_vouts)
        add_utxos_to_set(self.utxo_set, self.__utxos_from_vouts)
        self.__utxos_from_vins.clear()
        self.__utxos_from_vouts.clear()
        self.__pointers_from_vouts.clear()
        self.__txs_removed.clear()

    def save_data(self, filename='blockchain.txt'):
        """将节点状态保存到文件"""
        with open(filename, mode='w', encoding='utf-8') as f:
            f.write(json.dumps(self.chain, cls=MyJSONEncoder))
            f.write('\n')
            f.write(json.dumps(self.txs, cls=MyJSONEncoder))
            f.write('\n')
            pool_txs = list(self.mem_pool.values())
            f.write(json.dumps(pool_txs, cls=MyJSONEncoder))
            f.write('\n')
            utxos = [utxo for utxo in self.utxo_set.values()]
            f.write(json.dumps(utxos, cls=MyJSONEncoder))
            f.write('\n')
            f.write(json.dumps(list(self.peer_nodes)))
            f.write('\n')
            f.write(json.dumps(self.candidate_block, cls=MyJSONEncoder))
            f.write('\n')
            orphan_txs = list(self.orphan_pool.values())
            f.write(json.dumps(orphan_txs, cls=MyJSONEncoder))
            f.write('\n')
            f.write(json.dumps(self.orphan_block, cls=MyJSONEncoder))
            f.write('\n')

    def load_data(self, filename='blockchain.txt'):
        """从文件恢复节点状态"""
        with open(filename, mode='r', encoding='utf-8') as f:
            lines = f.readlines()
            chain = json.loads(lines[0])
            self.chain = [Block.from_dict(block) for block in chain]
            txs = json.loads(lines[1])
            self.txs = [Tx.from_dict(tx) for tx in txs]

            pool_txs = json.loads(lines[2])
            self.mem_pool.clear()
            for tx_dic in pool_txs:
                tx = Tx.from_dict(tx_dic)
                self.mem_pool[tx.id] = tx

            utxos = json.loads(lines[3])
            self.utxo_set.clear()
            for utxo_dic in utxos:
                utxo = UTXO.from_dict(utxo_dic)
                self.utxo_set[utxo.pointer] = utxo

            self.peer_nodes = set(json.loads(lines[4]))
            self.candidate_block = Block.from_dict(json.loads(lines[5]))

            orphan_txs = json.loads(lines[6])
            self.orphan_pool.clear()
            for tx_dic in orphan_txs:
                tx = Tx.from_dict(tx_dic)
                self.orphan_pool[tx.id] = tx

            orphan_blocks = json.loads(lines[7])
            self.orphan_block = [Block.from_dict(block) for block in orphan_blocks]

    def add_peer(self, addr: str, port: int = None):
        """添加广播邻居"""
        if port is None:
            self.peer_nodes.add(f'{addr}')
        else:
            self.peer_nodes.add(f'{addr}:{port}')


if __name__ == '__main__':
    peer = Peer()
    peer.generate_key()
    peer.save_data()
