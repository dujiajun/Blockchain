from typing import List

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

    def set_script(self, script: List, message: bytes = b''):
        """
        设置脚本
        :param script: 脚本
        :param message: 签名明文
        """
        self.clear()
        self.result = True
        self.pointer = 0
        self.message = message
        self.script = script

    def clear(self):
        """清空栈"""
        self.stack.clear()

    def top(self):
        """栈顶元素"""
        return self.stack[-1] if len(self.stack) > 0 else None

    def pop(self):
        """出栈"""
        return self.stack.pop()

    def push(self, value):
        """入栈"""
        self.stack.append(value)

    def eval(self, op):
        """
        执行指令
        :param op: 指令
        """
        if op in self.map:
            self.map[op]()
        elif isinstance(op, str) or \
                isinstance(op, bytes) or \
                isinstance(op, int) or \
                isinstance(op, bool):
            self.push(op)

    def add(self):
        """定义加法：栈顶与次栈顶出栈，相加结果入栈"""
        self.push(self.pop() + self.pop())

    def minus(self):
        """定义减法：栈顶减去次栈顶，结果入栈"""
        last = self.pop()
        self.push(self.pop() - last)

    def multiply(self):
        """定义乘法：栈顶与次栈顶出栈，相乘结果入栈"""
        self.push(self.pop() * self.pop())

    def dup(self):
        """复制栈顶元素并入栈"""
        self.push(self.top())

    def ndup(self):
        """复制n个元素到栈顶"""
        n = self.pop()
        for val in self.stack[-n:]:
            self.push(val)
        self.push(n)

    def equal_check(self):
        """判断栈顶与次栈顶是否相等，不相等结束运行"""
        flag = (self.pop() == self.pop())
        if not flag:
            self.result = False

    def equal(self):
        """判断栈顶与次栈顶是否相等，结果入栈"""
        self.push(self.pop() == self.pop())

    def check_sig(self):
        """验证签名"""
        pk_str = self.pop()
        sig = self.pop()
        vk = ecdsa.VerifyingKey.from_string(pk_str, curve=Params.CURVE)
        try:
            vk.verify(sig, self.message)
            self.push(True)
        except ecdsa.BadSignatureError:
            self.push(False)

    def calc_addr(self):
        """计算地址"""
        pk_str = self.pop()
        self.push(convert_pubkey_to_addr(pk_str))

    def check_mulsig(self):
        """验证多重签名"""
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
        """计算多公钥哈希值"""
        n = self.pop()
        pk_strs = [self.pop() for _ in range(n)]
        s = b''
        for val in pk_strs[::-1]:
            s += val
        self.push(sha256d(s))

    def run(self):
        """运行堆栈机"""
        while self.pointer < len(self.script):
            op = self.script[self.pointer]
            self.pointer += 1
            self.eval(op)
        if not self.result:
            return False
        else:
            return self.top()
