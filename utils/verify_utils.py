import ecdsa

from blockchain.block import Block
from blockchain.consensus import calculate_target
from blockchain.params import Params
from blockchain.transaction import Tx
from blockchain.wallet import Wallet
from utils.hash_utils import convert_pubkey_to_addr
from utils.log import logger
from utils.transaction_utils import add_tx_to_mem_pool, calculate_fees


def verify_tx_basic(tx):
    """
    验证交易基本条件
    :param tx: 欲验证对象
    :return: 是否为一个Tx对象
    """
    if not isinstance(tx, Tx):
        return False
    if (not tx.tx_out) or (not tx.tx_in):
        return False
    return True


def verify_double_payment(tx, pool):
    """
    :param tx: 交易对象
    :param pool: 交易池
    :return: 是否存在双重支付
    """
    if tx.id in pool:
        return True
    a = {vin.to_spend for vin in tx.tx_in}
    b = {vin.to_spend for tx in pool.values() for vin in tx.tx_in}
    return a.intersection(b)


def verify_signature_for_vin(vin, utxo, tx_out):
    """
    验证交易创建者是否拥有输入单元所使用的UTXO所有权
    :param vin: 输入单元
    :param utxo: UTXO对象
    :param tx_out: 输出列表
    :return: 签名是否匹配
    """
    pk_str, sig = vin.pubkey, vin.signature
    to_addr = utxo.vout.to_addr
    pk_as_addr = convert_pubkey_to_addr(pk_str)
    if pk_as_addr != to_addr:  # 地址是否匹配
        logger.debug("签名地址不匹配")
        return False
    vk = ecdsa.VerifyingKey.from_string(pk_str, curve=Params.CURVE)
    message = Wallet.create_signature_message(pk_str, vin.to_spend, tx_out)
    try:
        vk.verify(sig, message)  # 数字签名是否匹配
        return True
    except ecdsa.BadSignatureError:
        logger.debug("数字签名验证失败")
        return False


def verify_tx(peer, tx, mem_pool):
    """
    验证交易是否合法
    :param peer: 节点对象
    :param tx: 交易
    :param mem_pool: 交易池
    :return: 是否合法
    """
    if not verify_tx_basic(tx):
        logger.debug("参数格式验证失败")
        return False
    if verify_double_payment(tx, mem_pool):
        logger.debug("存在双重支付")
        return False
    available_value = 0
    for vin in tx.tx_in:
        utxo = peer.utxo_set.get(vin.to_spend, None)
        if not utxo:  # UTXO不存在就加入到孤儿交易池中
            peer.orphan_pool[tx.id] = tx
            logger.debug("交易使用的UTXO不存在，交易将被加入到孤立交易池中")
            return False
        if not verify_signature_for_vin(vin, utxo, tx.tx_out):
            return False
        available_value += utxo.vout.value
    if available_value < sum(vout.value for vout in tx.tx_out):
        logger.debug("输入金额小于输出金额")
        return False
    return True


def verify_tx_in_orphan_pool(peer):
    """
    验证peer中的孤儿交易池中是否有交易通过验证
    :param peer: 结点
    """
    copy_pool = peer.orphan_pool.copy()
    for tx in copy_pool.values():
        if not verify_tx(peer, tx, peer.mem_pool):
            continue
        add_tx_to_mem_pool(peer, tx)
        del peer.orphan_pool[tx.id]


def verify_coinbase(tx, reward):
    """
    验证交易是否为创币交易
    :param tx: 交易
    :param reward: 金额
    :return: 验证结果
    """
    if not isinstance(tx, Tx):
        return False
    if not tx.is_coinbase:
        return False
    if (not (len(tx.tx_out) == 1)) or (tx.tx_out[0].value != reward):
        return False
    return True


def verify_block_basic(block):
    """
    验证区块基本信息是否合法
    :param block: 区块
    :return: 是否合法
    """
    if not isinstance(block, Block):
        return False
    # 检查PoW是否正确
    if int(block.hash, 16) > calculate_target(block.bits):
        return False
    return True


def verify_double_payment_in_block(txs):
    """
    验证区块中的交易是否存在双重支付
    :param txs: 交易列表
    :return: 是否合法
    """
    a = [vin.to_spend for tx in txs for vin in tx.tx_in]
    b = {vin.to_spend for tx in txs for vin in tx.tx_in}
    return len(a) != len(b)


def verify_block_txs(block, reward):
    """
    验证区块交易基本信息是否合法
    :param reward: 区块奖励
    :param block: 区块
    :return: 是否合法
    """
    txs = block.txs
    if not isinstance(txs, list):
        return False
    # 区块至少需要2条交易，1条挖矿奖励，1条正常交易
    if len(txs) < 2:
        logger.debug("区块内交易数量不足2条")
        return False
    # 第1条交易需要是创币交易
    if not verify_coinbase(txs[0], reward):
        logger.debug("区块交易第1条非创币交易")
        return False
    return True


def verify_block(peer, block):
    """
    验证区块是否合法
    :param peer: 节点对象
    :param block: 区块
    :return: 是否合法
    """
    # if block == peer.candidate_block:
    #     return True
    if not verify_block_basic(block):
        logger.debug("区块类型错误")
        return False
    block_txs = block.txs[1:]
    rewards = Params.MINING_REWARDS + calculate_fees(block_txs)
    if not verify_block_txs(block, rewards):
        logger.debug("区块内交易类型错误")
        return False
    if verify_double_payment_in_block(block_txs):
        logger.debug("区块交易存在双重支付")
        return False
    for tx in block_txs:
        if not verify_tx(peer, tx, {}):
            return False
    return True


def locate_block_by_hash(chain, prev_hash):
    """
    在区块链中定位区块
    :param chain: 区块链
    :param prev_hash: 前一区块的哈希
    :return: 区块的高度
    """
    for height, block in enumerate(chain):
        if block.hash == prev_hash:
            return height + 1
    return -1
