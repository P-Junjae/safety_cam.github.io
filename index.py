import os
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

# Renderが提供する環境変数からデータベースURLを取得
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """データベース接続を確立する関数"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")
    return psycopg2.connect(DATABASE_URL)

@app.route('/', methods=['GET'])
def home():
    """ホームエンドポイント"""
    return "Hello, this is the Render API server for the Safety Cam project."

@app.route('/api/test', methods=['GET'])
def test_connection():
    """データベース接続をテストするエンドポイント"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return jsonify({"message": "Successfully connected to PostgreSQL!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """ユーザー登録エンドポイント"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "Missing username or password"}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ユーザー名の重複チェック
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
        if cursor.fetchone()[0] > 0:
            return jsonify({"success": False, "message": "Username already exists."}), 409
        
        # パスワードのハッシュ化（PostgreSQLではアプリ側で処理）
        # bcryptなどを使用するのが一般的だが、ここでは簡略化のためパスワードをそのまま保存
        # 実際にはpassword_hashカラムにハッシュ化したパスワードを保存
        sql = "INSERT INTO users (username, password_hash, email, full_name, role) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (username, password, 'dummy@example.com', '新規ユーザー', 'teacher'))
        conn.commit()
        
        return jsonify({"success": True, "message": "Registration successful!"}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Database error: " + str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)