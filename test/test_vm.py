import unittest

from vm import StackMachine


class TestStackMachine(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = StackMachine()

    def test_add(self):
        script = [2, 3, 'OP_ADD', 5, 'OP_EQUAL']
        self.machine.set_script(script)
        self.assertEqual(True, self.machine.run())

    def test_dup(self):
        script = [1, 'I', 'U', 'OP_DUP']
        self.machine.set_script(script)
        self.assertEqual('U', self.machine.run())

    def test_ndup(self):
        script = [1, 'I', 'U', 2, 'OP_NDUP']
        self.machine.set_script(script)
        self.assertEqual(2, self.machine.run())

    def test_addr(self):
        script = [1, b'I', b'U', 'OP_ADDR']
        self.machine.set_script(script)
        self.assertEqual('15Kx26NBHA2521LZWYe9GHcgPa9PMKvPGj', self.machine.run())

    def test_mulhash(self):
        script = [1, b'I', b'U', 2, 'OP_MULHASH']
        self.machine.set_script(script)
        self.assertEqual('732a89979416a90e1a28f20a0ca9aa453936b37847a76a7ee769e1e4f343daef', self.machine.run())


if __name__ == '__main__':
    unittest.main()
