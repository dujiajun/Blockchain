from typing import NamedTuple

from datatype.Transaction import Vout, Pointer


class UTXO(NamedTuple):
    vout: Vout
    pointer: Pointer
    is_coinbase: bool
    unspent: bool = True
    confirmed: bool = False

    @property
    def pubkey_script(self) -> str:
        return self.vout.pubkey_script

    def replace(self, unspent: bool = True, confirmed: bool = False):
        return UTXO(self.vout, self.pointer, self.is_coinbase, unspent, confirmed)

    def __repr__(self):
        return "UTXO(vout:{0}, pointer:{1})".format(self.vout, self.pointer)
