from typing import Union

from utils.CryptoUtils import sha256d


class Node(object):
    def __init__(self, data, pre_hased=False):
        if pre_hased:
            self.val = data
        else:
            self.val = sha256d(data)
        self.left_child = None
        self.right_child = None
        self.parent: Union[Node, None] = None
        self.bro: Union[Node, None] = None
        self.side: Union[str, None] = None


class MerkleTree(object):
    def __init__(self, leaves=None):
        self.leaves = [Node(leaf, True) for leaf in leaves]
        self.root: Union[Node, None] = None

    def add_node(self, leaf: Node):
        self.leaves.append(Node(leaf))

    def clear(self):
        self.root = None
        for leaf in self.leaves:
            leaf.parent, leaf.bro, leaf.side = (None,) * 3

    def get_root(self):
        if not self.leaves:
            return None
        level = self.leaves[::]
        while len(level) != 1:
            level = self._build_new_level(level)
        self.root = level[0]
        return self.root.val

    @classmethod
    def _build_new_level(cls, leaves):
        new, odd = [], None
        if len(leaves) % 2 == 1:
            odd = leaves.pop(-1)
        for i in range(0, len(leaves), 2):
            newnode = Node(leaves[i].val + leaves[i + 1].val)
            newnode.left_child, newnode.right_child = leaves[i], leaves[i + 1]
            leaves[i].side, leaves[i + 1].side = 'LEFT', 'RIGHT'
            leaves[i].parent, leaves[i + 1].parent = newnode, newnode
            leaves[i].bro, leaves[i + 1].bro = leaves[i + 1], leaves[i]
            new.append(newnode)
        if odd:
            new.append(odd)
        return new

    def get_path(self, index: int):
        path = []
        this = self.leaves[index]
        path.append((this.val, 'SELF'))
        while this.parent:
            path.append((this.bro.val, this.bro.side))
            this = this.parent
        path.append((this.val, 'ROOT'))
        return path


if __name__ == '__main__':
    merkle = MerkleTree(['a', 'b', 'c', 'd'])
    root = merkle.get_root()
    path = merkle.get_path(0)
    print(root)
    print(path)
