from flask import Flask, send_from_directory

app = Flask(__name__)
CORS(app)


@app.route('/')
def hello_world():
    return send_from_directory('ui', 'node.html')


if __name__ == '__main__':
    app.run()
