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
    data = {
        "grades":   db.get_distinct("grade"),
        "cuts":     db.get_distinct("cut"),
        "genders":  db.get_distinct("gender"),
        "storages": db.get_distinct("storage"),
    }
    return jsonify(data)


if __name__ == "__main__":
    db.init_db()
    app.run(port=5050, debug=True)
