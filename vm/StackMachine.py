from typing import List

import ecdsa

from params.Params import Params
from utils import CryptoUtils
from utils.CryptoUtils import sha256d


class StackMachine(object):
    def __init__(self):
        self.stack = []
        self._ops = {
            "OP_ADD": self.add,
            "OP_MINUS": self.minus,
            "OP_MUL": self.mul,
            "OP_EQ": self.equal_check,
            "OP_EQUAL": self.equal,
            "OP_CHECKSIG": self.check_sig,
            "OP_ADDR": self.calc_addr,
            "OP_DUP": self.dup,
            "OP_NDUP": self.ndup,
            "OP_CHECKMULSIG": self.check_mulsig,
            "OP_MULHASH": self.calc_mulhash
        }
        self.result = True
        self.pointer = 0
        self.message = b''
        self.script: List = []

    def set_script(self, script: List, message=b''):
        self.clear()
        self.result = True
        self.pointer = 0
        self.message = message
        self.script = script

    def clear(self):
        self.stack.clear()

    def push(self, value):
        self.stack.append(value)

    def pop(self):
        if self.stack:
            return self.stack.pop()

    def top(self):
        if self.stack:
            return self.stack[-1]

    def empty(self):
        return bool(self.stack)

    def eval(self, op):
        if op in self._ops:
            self._ops[op]()
        elif isinstance(op, str) or \
                isinstance(op, bytes) or \
                isinstance(op, int) or \
                isinstance(op, bool):
            self.push(op)

    def add(self):
        self.push(self.pop() + self.pop())

    def minus(self):
        last = self.pop()
        self.push(self.pop() - last)

    def mul(self):
        self.push(self.pop() * self.pop())

    def dup(self):
        self.push(self.top())

    def ndup(self):
        n = self.pop()
        for val in self.stack[-n:]:
            self.push(val)
        self.push(n)

    def equal_check(self):
        flag = (self.pop() == self.pop())
        if not flag:
            self.result = False

    def equal(self):
        self.push(self.pop() == self.pop())

    def check_sig(self):
        pk_str = self.pop()
        sig = self.pop()
        vk = ecdsa.VerifyingKey.from_string(pk_str, curve=Params.CURVE)
        flag = True
        try:
            vk.verify(sig, self.message)
        except ecdsa.BadSignatureError:
            flag = False
        self.push(flag)

    def calc_addr(self):
        pk = self.pop()
        self.push(CryptoUtils.convert_pubkey_to_addr(pk))

    def check_mulsig(self):
        n = self.pop()
        pk_s = [self.pop() for _ in range(n)]
        m = self.pop()
        sigs = [self.pop() for _ in range(m)]
        pk_s = pk_s[-m:]
        for i in range(m):
            vk = ecdsa.VerifyingKey.from_string(pk_s[i], curve=Params.CURVE)
            try:
                flag = vk.verify(sigs[i], self.message)
            except ecdsa.BadSignatureError:
                flag = False
            if not flag:
                break
            self.push(flag)

    def calc_mulhash(self):
        n = self.pop()
        pk_s = [self.pop() for _ in range(n)]
        s = b''
        for val in pk_s[::-1]:
            s += val
        self.push(CryptoUtils.sha256d(s))

    def run(self):
        while self.pointer < len(self.script):
            op = self.script[self.pointer]
            self.pointer += 1
            self.eval(op)

        if not self.result:
            return False
        else:
            return self.top()


if __name__ == '__main__':
    machine = StackMachine()
    kA = 3453543
    kB = 2349334
    skA = ecdsa.SigningKey.from_secret_exponent(kA, curve=Params.CURVE)
    skB = ecdsa.SigningKey.from_secret_exponent(kB, curve=Params.CURVE)
    pkA = skA.get_verifying_key()
    pkB = skB.get_verifying_key()
    message = b'I love blockchain'

    sigA = skA.sign(message)
    sigB = skB.sign(message)
    Hash = sha256d(pkA.to_string() + pkB.to_string())
    sig_script = [sigA, sigB, 2, pkA.to_string(), pkB.to_string(), 2]
    pubkey_script = ['OP_NDUP', 'OP_MULHASH', Hash, 'OP_EQ', 2, 'OP_CHECKMULSIG']
    script = sig_script + pubkey_script
    machine.set_script(script, message)
    print(machine.run())
