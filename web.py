import json
from argparse import ArgumentParser

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from peer import Peer
from utils.json_utils import MyJSONEncoder
from utils.log import logger

app = Flask(__name__)
CORS(app)
app.json_encoder = MyJSONEncoder
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


def notify(event: str, message: str):
    socketio.emit(event, message)


parser = ArgumentParser()
parser.add_argument('-p', '--port', type=int, default=5000)
args = parser.parse_args()
port = args.port

peer = Peer(port=port, ws_notify=notify)
peer.init()
peer.p2p_run()


@app.route('/')
def hello_world():
    return send_from_directory('ui', 'node.html')


@app.route('/save-data', methods=['POST'])
def save_data():
    try:
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
    return jsonify(peer.peer_nodes)


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


@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    if peer.broadcast_block():
        response = {'message': '已广播！'}
    else:
        response = {'message': '未广播！'}
    socketio.emit('notify', 'broadcast block')
    return jsonify(response)


@app.route('/update-chain', methods=['POST'])
def update_chain():
    if peer.update_chain():
        response = {'message': '已更新区块链！'}
        socketio.emit('notify', 'update chain')
    else:
        response = {'message': '未更新区块链！'}
    return jsonify(response)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=port)
