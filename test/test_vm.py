import unittest

import ecdsa

from params import Params
from transaction import Tx, Pointer, Vin
from utils.hash_utils import convert_pubkey_to_addr, sha256d
from vm import StackMachine


class TestStackMachine(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = StackMachine()

    def test_add(self):
        script = [2, 3, 'OP_ADD', 5, 'OP_EQUAL']
        self.machine.set_script(script)
        self.assertEqual(self.machine.run(), True)

    def test_dup(self):
        script = [1, 'I', 'U', 'OP_DUP']
        self.machine.set_script(script)
        self.assertEqual(self.machine.run(), 'U')

    def test_ndup(self):
        script = [1, 'I', 'U', 2, 'OP_NDUP']
        self.machine.set_script(script)
        self.assertEqual(self.machine.run(), 2)

    def test_addr(self):
        script = [1, b'I', b'U', 'OP_ADDR']
        self.machine.set_script(script)
        self.assertEqual(self.machine.run(), '15Kx26NBHA2521LZWYe9GHcgPa9PMKvPGj')

    def test_mulhash(self):
        script = [1, b'I', b'U', 2, 'OP_MULHASH']
        self.machine.set_script(script)
        self.assertEqual(self.machine.run(), '732a89979416a90e1a28f20a0ca9aa453936b37847a76a7ee769e1e4f343daef')

    def test_verify_signature(self):
        k = 3457534
        sk = ecdsa.SigningKey.from_secret_exponent(k, curve=Params.CURVE)
        pk = sk.get_verifying_key()
        addr = convert_pubkey_to_addr(pk.to_string())
        coinbase = Tx.create_coinbase(addr, 100)
        pointer = Pointer(coinbase.id, 0)
        message = b'I love blockchain'
        sig = sk.sign(message)
        vin = Vin(pointer, sig, pk.to_string())
        vout = coinbase.tx_out[0]
        sig_script = [vin.sig_script[:64], vin.sig_script[64:]]
        pubkey_script = vout.pubkey_script.split(' ')
        script = sig_script + pubkey_script
        self.machine.set_script(script, message)
        self.assertEqual(self.machine.run(), True)

    def test_verify_mulsig(self):
        kA = 3453543
        kB = 2349334
        skA = ecdsa.SigningKey.from_secret_exponent(kA, curve=Params.CURVE)
        skB = ecdsa.SigningKey.from_secret_exponent(kB, curve=Params.CURVE)
        pkA = skA.get_verifying_key()
        pkB = skB.get_verifying_key()
        message = b'I love blockchain'
        sigA = skA.sign(message)
        sigB = skB.sign(message)
        mulhash = sha256d(pkA.to_string() + pkB.to_string())
        sig_script = [sigA, sigB, 2, pkA.to_string(), pkB.to_string(), 2]
        pubkey_script = ['OP_NDUP', 'OP_MULHASH', mulhash, 'OP_EQ', 2, 'OP_CHECKMULSIG']
        self.machine.set_script(sig_script + pubkey_script, message)
        self.assertEqual(self.machine.run(), True)


if __name__ == '__main__':
    unittest.main()
