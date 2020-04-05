import ecdsa

from params import Params
from utils.hash_utils import convert_pubkey_to_addr, sha256d


class StackMachine(object):
    def __init__(self):
        self.stack = []
        self.map = {"OP_ADD": self.add,
                    "OP_MINUS": self.minus,
                    "OP_MUL": self.multiply,
                    "OP_EQ": self.equal_check,
                    "OP_EQUAL": self.equal,
                    "OP_CHECKSIG": self.check_sig,
                    "OP_ADDR": self.calc_addr,
                    "OP_DUP": self.dup,
                    "OP_NDUP": self.ndup,
                    "OP_CHECKMULSIG": self.check_mulsig,
                    "OP_MULHASH": self.calc_mulhash}
        self.result = True
        self.pointer = 0
        self.message = b''
        self.script = ""

    def set_script(self, script, message=b''):
        self.clear()
        self.result = True
        self.pointer = 0
        self.message = message
        self.script = script

    def clear(self):
        self.stack.clear()

    def top(self):
        return self.stack[-1]

    def pop(self):
        return self.stack.pop()

    def push(self, value):
        self.stack.append(value)

    def eval(self, op):
        if op in self.map:
            self.map[op]()
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

    def multiply(self):
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
        try:
            vk.verify(sig, self.message)
            self.push(True)
        except ecdsa.BadSignatureError:
            self.push(False)

    def calc_addr(self):
        pk_str = self.pop()
        self.push(convert_pubkey_to_addr(pk_str))

    def check_mulsig(self):
        n = self.pop()
        pk_strs = [self.pop() for _ in range(n)]
        m = self.pop()
        sigs = [self.pop() for _ in range(m)]
        pk_strs = pk_strs[-m:]
        for i in range(m):
            vk = ecdsa.VerifyingKey.from_string(pk_strs[i], curve=Params.CURVE)
            flag = True
            try:
                vk.verify(sigs[i], self.message)
            except ecdsa.BadSignatureError:
                flag = False
            if not flag:
                break
            self.push(flag)

    def calc_mulhash(self):
        n = self.pop()
        pk_strs = [self.pop() for _ in range(n)]
        s = b''
        for val in pk_strs[::-1]:
            s += val
        self.push(sha256d(s))

    def run(self):
        while self.pointer < len(self.script):
            op = self.script[self.pointer]
            self.pointer += 1
            self.eval(op)
        if not self.result:
            return False
        else:
            return self.top()
