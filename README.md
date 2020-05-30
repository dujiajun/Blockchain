# Blockchain

本项目为本人的毕业设计《基于树莓派的区块链技术开发实践》

## 起步

### 环境
* Python >= 3.7
* flask
* ecdsa
* base58
* httpx
* flask-cors
* flask-socketio
* eventlet
* matplotlib
* numpy

### 安装
建议使用conda或virtualenv新建虚拟环境。
```shell script
virtualenv venv
source ./venv/bin/activate
```

安装依赖。
```shell script
pip install -r requirements.txt
```


### 运行

首先启动Web服务。
```shell script
python web.py
```
然后在浏览器中打开`127.0.0.1:5000`即可访问项目界面。

若需要更改端口号，可以通过`-p`参数指定端口
```shell script
python web.py -p 5001
```
