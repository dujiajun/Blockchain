from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from peer import Peer
from utils.json_utils import MyJSONEncoder

app = Flask(__name__)
CORS(app)
app.json_encoder = MyJSONEncoder

peer = Peer()
peer.generate_key()
peer.create_genesis_block()


@app.route('/')
def hello_world():
    return send_from_directory('ui', 'node.html')


@app.route('/wallet', methods=['GET'])
def get_keys():
    response = {
        'addr': peer.addr,
        'pk': peer.pk.hex() if peer.pk else None,
        'sk': peer.sk.hex() if peer.sk else None,
        'balance': peer.get_balance()
    }
    print(response)
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
    return jsonify(peer.mem_pool.values())


@app.route('/utxo-set', methods=['GET'])
def get_utxo_set():
    response = [utxo for utxo in peer.utxo_set.values()]
    print(response)
    return jsonify(response)


@app.route('/txs', methods=['GET'])
def get_txs():
    return jsonify(peer.txs)


@app.route('/transaction', methods=['POST'])
def create_transaction():
    if peer.wallet.empty():
        response = {'message': '钱包未初始化！'}
        return jsonify(response)
    print(request.form)
    addr = request.form['addr']
    value = request.form['value']
    print(addr, value)
    res = peer.create_transaction(addr, value)
    if res:
        response = peer.txs
        return jsonify(response)
    else:
        response = {'message': '创建交易失败！'}
        return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
