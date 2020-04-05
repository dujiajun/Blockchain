import unittest

import ecdsa

from wallet import Wallet


class TestWallet(unittest.TestCase):
    def setUp(self) -> None:
        self.wallet = Wallet()
        self.wallet.generate_key()

    def test_empty(self):
        self.assertFalse(self.wallet.empty())

    def test_generate_keys(self):
        sk = self.wallet.sk.to_string()
        self.wallet.generate_key()
        self.assertNotEqual(self.wallet.sk.to_string(), sk)

    def test_sign(self):
        message = b'I love blockchain'
        sig = self.wallet.sign(message)
        pk = self.wallet.pk
        self.assertTrue(pk.verify(sig, message))
        with self.assertRaises(ecdsa.BadSignatureError):
            pk.verify(sig, b'123')


if __name__ == '__main__':
    unittest.main()
