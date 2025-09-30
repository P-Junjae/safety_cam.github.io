# requests.txt
Flask
mysql-connector-python

# api/index.py
import os
from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        db_connection = mysql.connector.connect(
            host=os.environ.get("DB_HOST","localhost"),
            user=os.environ.get("DB_USER","test"),
            password=os.environ.get("DB_PASSWORD","123"),
            DB_NAME = os.environ.get("DB_NAME", "safety_cam")
        )
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM your_table_name")
        records = cursor.fetchall()
        cursor.close()
        db_connection.close()
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return "Welcome to My Vercel API with MySQL!"
