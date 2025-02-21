from flask import Flask, render_template, jsonify, request
import os
from database import get_db_connection  # Подключаем MySQL
from bot import start_monitoring, stop_monitoring, is_monitoring

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", monitoring=is_monitoring())

@app.route("/logs")
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(logs)

@app.route("/start_monitoring", methods=["POST"])
def start():
    start_monitoring()
    return jsonify({"status": "started"})

@app.route("/stop_monitoring", methods=["POST"])
def stop():
    stop_monitoring()
    return jsonify({"status": "stopped"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
