from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import db

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return send_from_directory("landing", "index.html")

@app.route("/landing/<path:filename>")
def landing_static(filename):
    return send_from_directory("landing", filename)


@app.route("/api/summary")
def summary():
    """히어로 섹션용: 사이트별 최저가 top 3"""
    rows = db.get_summary()
    return jsonify(rows)


@app.route("/api/prices")
def prices():
    """
    조건 필터링 최저가 목록
    query params: grade, cut, gender
    """
    grade   = request.args.get("grade")
    cut     = request.args.get("cut")
    gender  = request.args.get("gender")
    storage = request.args.get("storage")

    rows = db.get_prices_filtered(grade=grade, cut=cut, gender=gender, storage=storage)
    return jsonify(rows)


@app.route("/api/meta")
def meta():
    """DB에 실제 존재하는 선택지 반환 (프론트 드롭다운 동적 구성용)"""
    import sqlite3, config
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    def distinct(col):
        return [r[0] for r in conn.execute(f"SELECT DISTINCT {col} FROM prices ORDER BY {col}").fetchall()]

    data = {
        "grades":   distinct("grade"),
        "cuts":     distinct("cut"),
        "genders":  distinct("gender"),
        "storages": distinct("storage"),
    }
    conn.close()
    return jsonify(data)


if __name__ == "__main__":
    db.init_db()
    app.run(port=5050, debug=True)
