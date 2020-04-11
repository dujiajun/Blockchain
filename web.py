import json
from argparse import ArgumentParser
from os.path import exists

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from peer import Peer, Tx, Block
from utils.json_utils import MyJSONEncoder
from utils.log import logger

app = Flask(__name__)
CORS(app)
app.json_encoder = MyJSONEncoder
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

peer = Peer()
if exists('wallet.txt'):
    peer.wallet.load_keys()
else:
    peer.generate_key()
if exists('genesis_block.txt'):
    peer.load_genesis_block()
if exists('blockchain.txt'):
    peer.load_data()


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
    return jsonify(response)


@app.route('/txs', methods=['GET'])
def get_txs():
    return jsonify(peer.txs)


@app.route('/orphan-pool', methods=['GET'])
def get_orphan_pool():
    response = [tx for tx in peer.orphan_pool.values()]
    return jsonify(response)


@app.route('/orphan-block', methods=['GET'])
def get_orphan_block():
    return jsonify(peer.orphan_block)


@app.route('/peers', methods=['GET'])
def get_peers():
    response = [node for node in peer.peer_nodes]
    return jsonify(response)


@app.route('/peers', methods=['POST'])
def add_peer():
    peer_node = request.form.get(key='node', type=str, default=None)
    if not peer_node:
        response = {'message': '参数错误！'}
        return jsonify(response)
    peer.add_peer(peer_node)
    response = [node for node in peer.peer_nodes]
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


@app.route('/receive-transaction', methods=['POST'])
def receive_transaction():
    src_addr = request.remote_addr
    src_port = request.form.get('port', type=int, default=None)
    peer.add_peer(src_addr, src_port)
    txs_str = request.form.get('txs', type=str)
    if txs_str is None:
        response = {'message': '参数错误！'}
        return jsonify(response)
    txs = json.loads(txs_str)
    for tx in txs:
        tx = Tx.from_dict(tx)
        res = peer.receive_transaction(tx)
        if not res:
            logger.debug("交易验证失败或已在交易池中！：" + str(tx))
    response = {'message': '已广播！'}
    socketio.emit('notify', 'received txs')
    return jsonify(response)


@app.route('/broadcast-txs', methods=['POST'])
def broadcast_txs():
    if peer.broadcast_txs():
        response = {'message': '已广播！'}
    else:
        response = {'message': '未广播！'}
    socketio.emit('notify', 'broadcast txs')
    return jsonify(response)


@app.route('/candidate-block', methods=['GET'])
def get_candidate_block():
    return jsonify(peer.candidate_block)


@app.route('/candidate-block', methods=['POST'])
def create_candidate_block():
    peer.create_candidate_block()
    return jsonify(peer.candidate_block)


@socketio.on('mine')
def mine(message):
    if peer.consensus():
        emit('mine', json.dumps(peer.candidate_block, cls=MyJSONEncoder))


@app.route('/receive-block', methods=['POST'])
def receive_block():
    src_addr = request.remote_addr
    src_port = request.form.get('port', type=int, default=None)
    peer.add_peer(src_addr, src_port)
    block_str = request.form.get('block', type=str)
    if block_str is None:
        response = {'message': '参数错误！'}
        return jsonify(response)
    block = Block.from_dict(json.loads(block_str))
    res = peer.receive_block(block)
    if not res:
        logger.debug("区块验证失败：" + str(block))
    response = {'message': '已广播！'}
    socketio.emit('notify', 'received block')
    return jsonify(response)


@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    if peer.broadcast_block():
        response = {'message': '已广播！'}
    else:
        response = {'message': '未广播！'}
    socketio.emit('notify', 'broadcast block')
    return jsonify(response)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000)
    args = parser.parse_args()
    port = args.port
    peer.port = port
    # app.run(host='0.0.0.0', port=port)
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
