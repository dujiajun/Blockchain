from transaction import UTXO, Pointer


def add_tx_to_mem_pool(peer, tx):
    """
    将交易加入到节点的交易池中
    :param peer: 节点
    :param tx: 交易
    """
    peer.mem_pool[tx.id] = tx
    if peer.allow_utxo_from_pool:
        add_utxos_from_tx_to_set(peer.utxo_set, tx)


def add_utxos_from_tx_to_set(utxo_set, tx):
    """
    将封装好的UTXO加入到UTXO集合中
    :param utxo_set: UTXO集合
    :param tx: 交易
    """
    utxos = find_utxos_from_tx(tx)
    for utxo in utxos:
        utxo_set[utxo.pointer] = utxo


def add_utxos_from_block_to_set(utxo_set, txs):
    """
    将区块中的交易UTXO写入集合中
    :param utxo_set: UTXO集合
    :param txs: 交易列表
    """
    utxos = find_utxos_from_block(txs)
    add_utxos_to_set(utxo_set, utxos)


def add_utxos_to_set(utxo_set, utxos):
    """
    将UTXO添加到集合中
    :param utxo_set: UTXO集合
    :param utxos: UTXO列表
    """
    if isinstance(utxos, dict):
        utxos = utxos.values()
    for utxo in utxos:
        utxo_set[utxo.pointer] = utxo


def delete_utxo_by_pointers(utxo_set, pointers):
    """
    从UTXO_SET中删去定位指针使用过的UTXO，并存储在列表中
    :param utxo_set: UTXO集合
    :param pointers: 定位指针集合
    :return: 被删掉的UTXO列表
    """
    utxos_from_vins = []
    for pointer in pointers:
        if pointer in utxo_set:
            utxos_from_vins.append(utxo_set[pointer])
            del utxo_set[pointer]
    return utxos_from_vins


def remove_spent_utxo_from_txs(utxo_set, txs):
    """
    移除使用过的UTXO
    :param utxo_set: UTXO集合
    :param txs: 交易列表
    :return: 移除后的UTXO列表
    """
    pointers = find_vin_pointer_from_txs(txs)
    utxos = delete_utxo_by_pointers(utxo_set, pointers)
    return utxos


def remove_txs_from_pool(pool, txs):
    """
    从交易池中移除区块交易
    :param pool: 交易池
    :param txs: 交易
    :return: 移除的交易，用于备份
    """
    n_txs = {}
    for tx in txs:
        if tx.id in pool:
            n_txs[tx.id] = tx
            del pool[tx.id]
    return n_txs


def remove_utxos_from_set(utxo_set, pointers):
    """
    从UTXO集合中删去指针指向的UTXO
    :param utxo_set: UTXO集合
    :param pointers: 定位指针
    """
    for pointer in pointers:
        if pointer in utxo_set:
            del utxo_set[pointer]


def find_vin_pointer_from_txs(txs):
    """
    找到交易的所有输入单元使用过的UTXO定位指针，并存储在列表中
    :param txs: 交易列表
    :return: 定位指针集合
    """
    return [vin.to_spend for tx in txs for vin in tx.tx_in]


def find_vout_pointer_from_txs(txs):
    """
    找到所有UTXO的定位指针
    :param txs:
    :return:
    """
    return [Pointer(tx.id, i) for tx in txs for i, vout in enumerate(tx.tx_out)]


def find_utxos_from_tx(tx):
    """
    从交易中所有的Vout封装成UTXO
    :param tx: 交易
    :return: UTXO列表
    """
    return [UTXO(vout=vout, pointer=Pointer(tx.id, i), is_coinbase=tx.is_coinbase)
            for i, vout in enumerate(tx.tx_out)]


def find_utxos_from_txs(txs):
    """
    从交易列表中构建UTXO列表
    :param txs: 交易列表
    :return: UTXO列表
    """
    return [UTXO(vout=vout, pointer=Pointer(tx.id, i), is_coinbase=tx.is_coinbase)
            for tx in txs for i, vout in enumerate(tx.tx_out)]


def find_utxos_from_block(txs):
    """
    从区块的交易列表中构建已确认的UTXO列表
    :param txs: 交易列表
    :return: UTXO列表
    """
    return [UTXO(vout=vout, pointer=Pointer(tx.id, i), is_coinbase=tx.is_coinbase,
                 unspent=True, confirmed=True)
            for tx in txs for i, vout in enumerate(tx.tx_out)]


def confirm_utxos_from_txs(utxo_set, txs, allow_utxo_from_pool):
    """
    添加UTXO至UTXO_SET
    :param utxo_set: UTXO集合
    :param txs: 交易
    :param allow_utxo_from_pool: 允许从交易池中提取有效UTXO
    :return:
    """
    if allow_utxo_from_pool:
        # 非创币交易找未确认的UTXO
        utxos = find_utxos_from_txs(txs[1:])
        # 所有输出单元均封装为UTXO，均为已确认
        add_utxos_from_block_to_set(utxo_set, txs)
        # 找到定位指针用于备份
        pointers = find_vout_pointer_from_txs(txs)
        return pointers, utxos
    else:
        # 找到所有输出单元的UTXO，状态已确认
        utxos = find_utxos_from_txs(txs)
        # 找到定位指针用于备份
        pointers = find_vout_pointer_from_txs(txs)
        add_utxos_to_set(utxo_set, utxos)
        return pointers, []


def sign_utxo_from_tx(utxo_set, tx):
    """
    从UTXO集合中将tx花费的UTXO标记出来
    :param utxo_set: UTXO集合
    :param tx: 交易
    """
    for vin in tx.tx_in:
        pointer = vin.to_spend
        utxo = utxo_set[pointer]
        utxo = utxo.replace(unspent=False)
        utxo_set[pointer] = utxo
