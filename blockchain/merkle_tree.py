from typing import Optional, List

from utils.hash_utils import sha256d
from utils.printable import Printable


def get_merkle_root_of_txs(txs) -> str:
    """
    从交易列表获取梅尔克树根哈希值
    :param txs: 交易列表
    :return: 哈希值
    """
    return get_merkle_root([tx.id for tx in txs])


def get_merkle_root(level) -> str:
    """
    从一层节点中求梅尔克树根哈希值
    :param level: 叶节点
    :return: 哈希值
    """
    while len(level) != 1:
        odd = None
        if len(level) % 2 == 1:
            odd = level.pop()

        level = [sha256d(i1 + i2) for i1, i2 in pair_node(level)]

        if odd:
            level.append(odd)
    return level[0]


def pair_node(level):
    """
    将一层节点两两配对
    :param level: 一层节点
    :return: 配对后的列表
    """
    return (level[i:i + 2] for i in range(0, len(level), 2))


class Node(Printable):
    """梅克尔树节点"""

    def __init__(self, data, pre_hashed=False):
        if pre_hashed:  # 如果是底层节点，哈希值为输入值
            self.val = data
        else:
            self.val = sha256d(data)

        self.left_child = None
        self.right_child = None
        self.parent = None
        self.bro = None
        self.side = None


def build_new_level(leaves):
    """构建新的层级"""
    new, odd = [], None
    if len(leaves) % 2 == 1:
        odd = leaves.pop(-1)
    for i in range(0, len(leaves), 2):
        newnode = Node(leaves[i].val + leaves[i + 1].val)
        newnode.lelf_child, newnode.right_child = leaves[i], leaves[i + 1]
        leaves[i].side, leaves[i + 1].side, = 'LEFT', 'RIGHT'
        leaves[i].parent, leaves[i + 1].parent = newnode, newnode
        leaves[i].bro, leaves[i + 1].bro = leaves[i + 1], leaves[i]
        new.append(newnode)
    if odd:
        new.append(odd)
    return new


class MerkleTree(Printable):
    """梅克尔树"""

    def __init__(self, leaves=None):
        """
        :param leaves: 底层节点的哈希值列表
        """
        if leaves is None:
            leaves = []
        self.root = None
        self.leaves = []
        self.set_leaves(leaves)

    def set_leaves(self, leaves):
        self.leaves = [Node(leaf, True) for leaf in leaves]
        self.root = None

    def add_node(self, leaf):
        """
        添加新节点
        :param leaf: 新节点
        """
        self.leaves.append(Node(leaf))

    def clear(self):
        """梅尔克树清零"""
        self.root = None
        for leaf in self.leaves:
            leaf.parent, leaf.bro, leaf.side = (None,) * 3

    def get_root(self) -> Optional[str]:
        """计算梅尔克树根节点哈希值"""
        if not self.leaves:
            return None

        level = self.leaves[::]
        while len(level) != 1:
            level = build_new_level(level)
        self.root = level[0]
        return self.root.val

    def get_path(self, index) -> List:
        """
        获取由底层节点计算根哈希值所需要的所有哈希值
        :param index: 底层节点在列表中的索引
        :return: 路径
        """
        path = []
        this = self.leaves[index]
        path.append((this.val, 'SELF'))
        while this.parent:
            path.append((this.bro.val, this.bro.side))
            this = this.parent
        path.append((this.val, 'ROOT'))
        return path
