import json

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from peer import Peer, Tx
from utils.json_utils import MyJSONEncoder
from utils.log import logger

app = Flask(__name__)
CORS(app)
app.json_encoder = MyJSONEncoder

peer = Peer()
peer.generate_key()
peer.create_genesis_block()


@app.route('/')
def hello_world():
    return send_from_directory('ui', 'node.html')


@app.route('/save-data', methods=['POST'])
def save_data():
    try:
        peer.wallet.save_keys()
        peer.save_data()
        res = True
    except Exception as e:
        logger.debug(e)
        res = False
    response = {'message': res}
    return jsonify(response)


@app.route('/load-data', methods=['POST'])
def load_data():
    try:
        peer.wallet.load_keys()
        peer.load_data()
        res = True
    except Exception as e:
        logger.debug(e)
        res = False
    response = {'message': res}
    return jsonify(response)


@app.route('/wallet', methods=['GET'])
def get_keys():
    response = {
        'addr': peer.addr,
        'pk': peer.pk.hex() if peer.pk else None,
        'sk': peer.sk.hex() if peer.sk else None,
        'balance': peer.get_balance()
    }
    # print(response)
    return jsonify(response)


@app.route('/wallet', methods=['POST'])
def generate_keys():
    peer.generate_key()
    response = {
        'addr': peer.addr,
        'pk': peer.pk.hex() if peer.pk else None,
        'sk': peer.sk.hex() if peer.sk else None,
        'balance': peer.get_balance()
    }
    return jsonify(response)


@app.route('/chain', methods=['GET'])
def get_chain():
    return jsonify(peer.chain)


@app.route('/mem-pool', methods=['GET'])
def get_mem_pool():
    response = [tx for tx in peer.mem_pool.values()]
    return jsonify(response)


@app.route('/utxo-set', methods=['GET'])
def get_utxo_set():
    response = [utxo for utxo in peer.utxo_set.values()]
    # print(response)
    return jsonify(response)


@app.route('/txs', methods=['GET'])
def get_txs():
    print(peer.txs)
    return jsonify(peer.txs)


@app.route('/peers', methods=['GET'])
def get_peers():
    response = [node for node in peer.peer_nodes]
    # print(response)
    return jsonify(response)


@app.route('/peers', methods=['POST'])
def add_peer():
    peer_node = request.form.get(key='node', type=str, default=None)
    if not peer_node:
        response = {'message': '参数错误！'}
        return jsonify(response)
    peer.peer_nodes.add(peer_node)
    response = [node for node in peer.peer_nodes]
    # print(response)
    return jsonify(response)


@app.route('/transaction', methods=['POST'])
def create_transaction():
    if peer.wallet.empty():
        response = {'message': '钱包未初始化！'}
        return jsonify(response)
    addr = request.form.get(key='addr', type=str, default=None)
    value = request.form.get(key='value', type=int, default=None)
    if not addr or not value or addr == '' or value <= 0:
        response = {'message': '参数错误！'}
        return jsonify(response)
    res = peer.create_transaction(addr, value)
    if res:
        response = peer.txs
        return jsonify(response)
    else:
        response = {'message': '创建交易失败！'}
        return jsonify(response)


@app.route('/broadcast-transaction', methods=['POST'])
def receive_transaction():
    txs_str = request.form.get('txs', type=str)
    txs = json.loads(txs_str)
    for tx in txs:
        tx = Tx.from_dict(tx)
        res = peer.receive_transaction(tx)
        if not res:
            logger.debug("交易" + str(tx) + "验证失败")
    # print("broadcast-transaction: " + txs)
    response = {'message': '已广播！'}
    return jsonify(response)


@app.route('/broadcast-txs', methods=['POST'])
def broadcast_txs():
    if peer.broadcast_txs():
        response = {'message': '已广播！'}
    else:
        response = {'message': '未广播！'}
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
