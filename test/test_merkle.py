import unittest

from blockchain.merkle_tree import *


class TestMerkle(unittest.TestCase):
    def setUp(self) -> None:
        self.merkle = MerkleTree(['a', 'b', 'c', 'd'])
        self.level = ['a', 'b', 'c', 'd']

    def test_merkle_root(self):
        self.assertEqual(self.merkle.get_root(), '20c12afdb2ce90da744e7f06424176c0c36f633be6cadd4eeafcda65855a7a73')
        self.assertEqual(self.merkle.get_root(), get_merkle_root(self.level))

    def test_get_path(self):
        root = self.merkle.get_root()
        path = [('a', 'SELF'),
                ('b', 'RIGHT'),
                ('032a3987db0858e6d3ebad8580da9f28774bd9e0158e78d6ef42a68869750e26', 'RIGHT'),
                ('20c12afdb2ce90da744e7f06424176c0c36f633be6cadd4eeafcda65855a7a73', 'ROOT')]
        computed_path = self.merkle.get_path(0)
        self.assertEqual(computed_path, path)
        ab = sha256d(computed_path[0][0] + computed_path[1][0])
        abcd = sha256d(ab + computed_path[2][0])
        self.assertEqual(abcd, root)


if __name__ == '__main__':
    unittest.main()
