import json
import threading
from os.path import exists
from typing import Dict, List, Optional

import httpx

from blockchain.consensus import mine
from blockchain.transaction import Vout, Vin
from p2p.node import P2PNode
from utils.json_utils import MyJSONEncoder
from utils.transaction_utils import *
from utils.verify_utils import *


def broadcast(peers: List[tuple], payload: dict, payload_type: str):
    """
    广播区块或者交易
    :param peers: 在线节点列表
    :param payload: 负载
    :param payload_type: 类型
    """
    for (ip, port) in peers:
        url = f"http://{ip}:{port}/receive-{payload_type}"
        if payload_type == 'txs':
            logger.info(f"广播交易：开始向{ip}:{port}广播离线交易")
        else:
            logger.info(f"广播区块：开始向{ip}:{port}广播区块")
        try:
            httpx.post(url, data=payload)
        except:
            logger.debug(f'向{ip}:{port}广播失败！')


class Peer:
    """区块链的参与者对象"""

    def __init__(self,
                 wallet_file: str = 'wallet_{0}.txt',
                 blockchain_file: str = 'blockchain_{0}.txt',
                 genesis_block_file: str = 'genesis_block.txt',
                 port: int = 5000,
                 ws_notify: Optional[callable] = None):
        """
        初始化
        :param wallet_file: 钱包文件地址
        :param blockchain_file: 本地区块链文件地址
        :param genesis_block_file: 创世区块文件地址
        :param port: 绑定的端口
        :param ws_notify: websocket回调函数
        """
        self.wallet_file = wallet_file.format(port)
        self.blockchain_file = blockchain_file.format(port)
        self.genesis_block_file = genesis_block_file

        self.chain = []
        self.txs = []  # 离线交易
        self.utxo_set: Dict[Pointer, UTXO] = {}
        self.mem_pool: Dict[str, Tx] = {}
        self.orphan_pool: Dict[str, Tx] = {}
        self.wallet = Wallet(self.wallet_file)
        self.allow_utxo_from_pool = False
        self.orphan_block = []
        self.candidate_block = None
        self.fee = Params.DEFAULT_FEE

        self.__utxos_from_vins = []
        self.__utxos_from_vouts = []
        self.__pointers_from_vouts = []
        self.__txs_removed = {}

        self.p2p_node = P2PNode(port=port, blockchain=self)
        self.ws_notify = ws_notify

        self.longest_node = None
        self.longest_chain_length = 0
        self.longest_lock = threading.Lock()

    def init(self):
        """从本地文件（若存在）初始化节点"""
        if exists(self.wallet_file):
            self.wallet.load_keys(self.wallet_file)
        else:
            self.generate_key()
        if exists(self.genesis_block_file):
            self.load_genesis_block()
        if exists(self.blockchain_file):
            self.load_data()

    def p2p_run(self):
        """运行P2P网络"""
        self.p2p_node.run()

    @property
    def peer_nodes(self):
        """
        获取P2P网络在线节点列表
        :return: 在线节点列表
        """
        return self.p2p_node.get_peers()

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

    def get_balance(self) -> int:
        """
        :return: 自身余额
        """
        utxos = self.get_utxos()
        return sum([utxo.vout.value for utxo in utxos])

    def create_transaction(self, to_addr: str, value: int) -> bool:
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
            message = self.wallet.create_signature_message(self.pk, utxo.pointer, tx_out)
            signature = self.wallet.sign(message)
            tx_in.append(Vin(to_spend=utxo.pointer, signature=signature, pubkey=self.pk))
            # self.utxo_set[utxo.pointer] = utxo.replace(unspent=False)
        tx = Tx(tx_in=tx_in, tx_out=tx_out, fee=self.fee)
        logger.info(f"创建交易：{tx}")
        self.txs.append(tx)
        return True

    def receive_transaction(self, tx: Tx) -> bool:
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
        logger.info(f"接收交易：验证交易失败或已在交易池中：{tx}")
        return False

    def broadcast_txs(self) -> bool:
        """广播所有离线交易"""
        # 无需广播
        if len(self.txs) == 0:
            logger.info("广播交易：离线交易为空")
            return False
        if len(self.peer_nodes) == 0:
            logger.info("广播交易：邻居为空")
            return False

        payload = {'txs': json.dumps(self.txs, cls=MyJSONEncoder)}
        peers = self.p2p_node.get_peers()
        broadcast(peers, payload, 'txs')
        self.txs.clear()
        return True

    def load_genesis_block(self, filename: str = 'genesis_block.txt') -> None:
        """加载创世区块"""
        with open(filename, mode='r') as f:
            line = f.readlines()[0]
            block_dic = json.loads(line)
            block = Block.from_dict(block_dic)
            self.chain = [block]
            utxos = find_utxos_from_block(block.txs)
            add_utxos_to_set(self.utxo_set, utxos)

    def create_candidate_block(self) -> bool:
        """
        构造候选区块
        :return: 区块
        """
        if len(self.mem_pool) == 0:
            return False
        prev_hash = self.chain[-1].hash
        txs = list(self.mem_pool.values())

        value = Params.MINING_REWARDS + calculate_fees(txs)
        coinbase = Tx.create_coinbase(self.addr, value)
        txs = [coinbase] + txs
        self.candidate_block = Block(prev_hash=prev_hash, nonce=0,
                                     bits=Params.DIFFICULTY_BITS, txs=txs)
        logger.info(f"创建候选区块：{self.candidate_block}")
        return True

    def consensus(self) -> bool:
        """
        进行共识
        :return: 修改nonce后的区块
        """
        if not self.candidate_block:
            if not self.create_candidate_block():
                return False
        block = self.candidate_block
        logger.info("共识：开始挖矿！")
        nonce = mine(block)
        logger.info(f"共识：挖矿结束，nonce={nonce}")
        self.candidate_block = block.replace(nonce=nonce)
        return True

    def broadcast_block(self) -> bool:
        """
        广播区块
        """
        # 无需广播
        if self.candidate_block is None:
            logger.info("广播区块：未创建候选区块")
            return False
        payload = {'block': json.dumps(self.candidate_block, cls=MyJSONEncoder)}
        peers = self.p2p_node.get_peers()
        broadcast(peers, payload, 'block')
        self.candidate_block = None
        return True

    def receive_block(self, block: Block) -> bool:
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

    def update_after_receive_block(self, txs: List[Tx]) -> None:
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

    def roll_back(self) -> None:
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

    def save_data(self) -> None:
        """将节点状态保存到文件"""
        self.wallet.save_keys(self.wallet_file)
        with open(self.blockchain_file, mode='w', encoding='utf-8') as f:
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
            f.write(json.dumps(self.candidate_block, cls=MyJSONEncoder))
            f.write('\n')
            orphan_txs = list(self.orphan_pool.values())
            f.write(json.dumps(orphan_txs, cls=MyJSONEncoder))
            f.write('\n')
            f.write(json.dumps(self.orphan_block, cls=MyJSONEncoder))
            f.write('\n')

    def load_data(self) -> None:
        """从文件恢复节点状态"""
        self.wallet.load_keys(self.wallet_file)
        with open(self.blockchain_file, mode='r', encoding='utf-8') as f:
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

            self.candidate_block = Block.from_dict(json.loads(lines[4]))

            orphan_txs = json.loads(lines[5])
            self.orphan_pool.clear()
            for tx_dic in orphan_txs:
                tx = Tx.from_dict(tx_dic)
                self.orphan_pool[tx.id] = tx

            orphan_blocks = json.loads(lines[6])
            self.orphan_block = [Block.from_dict(block) for block in orphan_blocks]

    def update_chain(self):
        """从P2P网络中获取最长链更新本地区块链"""
        self.longest_lock.acquire()
        longest_node = self.longest_node
        self.longest_lock.release()
        logger.info('开始更新区块链！')
        if longest_node is None:
            logger.info('当前无比自己更长的链')
            return False
        try:
            url = f'http://{longest_node[0]}:{longest_node[1]}/chain'
            response = httpx.get(url)
            self.replace_chain(response.json())
            return True
        except:
            logger.debug(f'访问{longest_node}区块链失败！')
            return False

    def replace_chain(self, chain_json):
        """替换本地区块链"""
        blocks = [Block.from_dict(block) for block in chain_json[1:]]
        self.chain.clear()
        self.utxo_set.clear()
        self.load_genesis_block(self.genesis_block_file)
        for block in blocks:
            self.receive_block(block)

    def notify(self, event: str, message: str):
        """
        通知Websocket发送消息
        :param event: 事件
        :param message: 消息
        """
        if self.ws_notify:
            self.ws_notify(event, message)

    def update_longest(self, length: int, addr: tuple):
        """
        更新最长链信息
        :param length: 链长度
        :param addr: 地址
        """
        self.longest_lock.acquire()
        if length > self.longest_chain_length:
            self.longest_chain_length = length
            self.longest_node = addr
        self.longest_lock.release()
