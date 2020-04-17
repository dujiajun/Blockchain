import threading
import time

import requests
from flask import Flask, request, jsonify

from p2p.config import SEED_PORT, UPDATE_INTERVAL
from utils.log import logger

app = Flask(__name__)
nodes = set()


@app.route('/login', methods=['POST'])
def login():
    ip = request.remote_addr
    port = request.form.get('port', default=5000)
    node = (ip, port)
    if node in nodes:
        return "当前节点已在在线节点列表中"
    else:
        nodes.add(node)
        return "添加成功"


@app.route('/nodes')
def get_nodes():
    return jsonify(list(nodes))


def keep_alive():
    while True:
        logger.info('开始检测心跳...')
        tmp = list(nodes)
        for node in tmp:
            url = f"http://{node[0]}:{node[1]}/keep-alive"
            try:
                requests.post(url)
            except:
                logger.info(f'{node}不在线，将被移除在线列表')
                nodes.remove(node)
        logger.info(f'当前在线列表：{nodes}')
        time.sleep(UPDATE_INTERVAL)


if __name__ == '__main__':
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.start()
    app.run(host='0.0.0.0', port=SEED_PORT)
