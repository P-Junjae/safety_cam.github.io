from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['GET'])
def get_data():
    # ここにデータベース（MySQL）からデータを取得する処理を記述
    # 現状はダミーデータを返す
    data = {
        "message": "Hello from Vercel API!",
        "status": "success"
    }
    return jsonify(data)

@app.route('/', methods=['GET'])
def home():
    return "Welcome to My Vercel API!"
