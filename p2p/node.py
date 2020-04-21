import json
import socket
import threading
from argparse import ArgumentParser
from enum import Enum
from time import sleep, time
from typing import Union, Dict, List, Optional

from p2p.config import *
from utils.json_utils import MyJSONEncoder
from utils.log import logger


class ActionType(Enum):
    """消息类型"""
    NEW_PEER = 'new_peer'
    PEERS = 'peers'
    INTRODUCE = 'introduce'
    HEARTBEAT_REQUEST = 'heartbeat_request'
    HEARTBEAT_RESPONSE = 'heartbeat_response'


def create_message(action_type: ActionType, data: Union[int, dict, str, set]) -> dict:
    """
    构建消息包对象
    :param action_type: 消息类型
    :param data: 消息内容
    :return: 消息包
    """
    if isinstance(data, set):
        data = list(data)
    message = {'type': action_type.value, 'data': data}
    return message


class P2PNode(object):
    """P2P节点对象"""

    def __init__(self, port: int, blockchain=None):
        """
        初始化
        :param port: 监听端口号
        """
        self.peers: set = set()
        self.peer_lives: Dict[tuple, int] = dict()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.peers_lock = threading.Lock()
        self.peer_lives_lock = threading.Lock()

        self.blockchain = blockchain

    def run(self):
        """启动P2P节点"""
        self.sock.bind(('0.0.0.0', self.port))
        thread_recv = threading.Thread(target=self.recv, args=())
        thread_keep_alive = threading.Thread(target=self.keep_alive, args=())
        thread_recv.start()
        thread_keep_alive.start()
        self.send_to_seed()

    def get_peers(self) -> List[tuple]:
        """
        获取在线节点列表
        :return: 在线节点列表
        """
        self.peers_lock.acquire()
        peers = list(self.peers.copy())
        self.peers_lock.release()
        return peers

    def recv(self):
        """接收消息"""
        while True:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
            except Exception as e:
                logger.debug(e)
                continue
            action = json.loads(data.decode(encoding='utf-8'))
            if action['type'] == ActionType.NEW_PEER.value:
                self.add_peer(addr)
                self.send_peers(addr)
            elif action['type'] == ActionType.PEERS.value:
                peers = [(addr[0], addr[1]) for addr in action['data']]
                self.peers.update(peers)
                self.broadcast_introduce()
            elif action['type'] == ActionType.INTRODUCE.value:
                if self.blockchain:
                    self.blockchain.notify('peer', 'new peers')
                self.add_peer(addr)
            elif action['type'] == ActionType.HEARTBEAT_REQUEST.value:
                self.send_heartbeat_response(addr)
            elif action['type'] == ActionType.HEARTBEAT_RESPONSE.value:
                self.blockchain.update_longest(action['data'], addr)
                self.add_peer(addr)
            self.refresh_peer_life(addr)

    def send(self, data: Union[dict, str, bytes], to: tuple):
        """发送消息"""
        if isinstance(data, dict):
            data = json.dumps(data, cls=MyJSONEncoder)
        if isinstance(data, str):
            data = data.encode(encoding='utf-8')
        try:
            self.sock.sendto(data, to)
        except:
            logger.warning(f'发送至{to}失败：{data}')

    def broadcast(self, data: Union[dict, str, bytes], to: Optional[List[tuple]] = None):
        """
        广播消息
        :param to: 广播对象
        :param data: 消息
        """
        self.peers_lock.acquire()
        to = to or self.peers.copy()
        self.peers_lock.release()

        for node in to:
            self.send(data, node)

    def send_peers(self, to: tuple):
        """
        发送节点列表
        :param to: 目标地址
        """
        self.send(create_message(ActionType.PEERS, self.peers), to)

    def broadcast_introduce(self):
        """广播自我介绍"""
        self.broadcast(create_message(ActionType.INTRODUCE, ''))

    def get_silent_peers(self) -> List[tuple]:
        """获取一段时间内未通信节点"""
        limit = int(time()) - ALIVE_TIMEOUT
        self.peer_lives_lock.acquire()
        silent_peers = [node for (node, last_time) in self.peer_lives.items() if last_time < limit]
        self.peer_lives_lock.release()
        return silent_peers

    def broadcast_heartbeat(self):
        """广播心跳包"""
        silent_peers = self.get_silent_peers()
        self.remove_peer(silent_peers)
        self.broadcast(create_message(ActionType.HEARTBEAT_REQUEST, ''), silent_peers)

    def send_heartbeat_response(self, to: tuple):
        """
        响应心跳包
        :param to: 回复地址
        """
        data = len(self.blockchain.chain) if self.blockchain else 0
        self.send(create_message(ActionType.HEARTBEAT_RESPONSE, data), to)

    def keep_alive(self):
        """心跳机制"""
        while True:
            self.broadcast_heartbeat()
            sleep(UPDATE_INTERVAL)

    def add_peer(self, addr: tuple):
        """
        添加新节点
        :param addr: 节点地址
        """
        self.peers_lock.acquire()
        self.peers.add(addr)
        self.peers_lock.release()

    def remove_peer(self, peers: List[tuple]):
        """
        移除节点
        :param peers: 节点地址
        """
        self.peers_lock.acquire()
        self.peer_lives_lock.acquire()
        for addr in peers:
            if addr in self.peers:
                self.peers.remove(addr)
            if addr in self.peer_lives:
                self.peer_lives.pop(addr)
        self.peer_lives_lock.release()
        self.peers_lock.release()

    def update_peers(self, peers: List[tuple]):
        """
        更新节点
        :param peers: 节点列表
        """
        self.peers_lock.acquire()
        self.peers.update(peers)
        self.peers_lock.release()

    def refresh_peer_life(self, addr: tuple):
        """
        刷新节点更新时间
        :param addr: 节点地址
        """
        self.peer_lives_lock.acquire()
        self.peer_lives[addr] = int(time())
        self.peer_lives_lock.release()

    def send_to_seed(self):
        """向种子服务器发送消息"""
        self.send(create_message(ActionType.NEW_PEER, ''), SEED_ADDR)


def main():
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000)
    args = parser.parse_args()
    port = args.port
    node = P2PNode(port)
    node.run()


if __name__ == '__main__':
    main()
