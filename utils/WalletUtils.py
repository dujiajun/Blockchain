from typing import List

from datatype.Transaction import Tx


def calculate_fees(txs: List[Tx]):
    return sum(tx.fee for tx in txs)


