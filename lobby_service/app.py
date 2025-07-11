from typing import Dict
from flask import Flask, request, jsonify
import requests
import logging
import uuid
import redis
import json
from flask_socketio import SocketIO, join_room, emit

WAITING = "waiting"

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

redis_client = redis.Redis(host=redis, port=6379, db=0)

socketio = SocketIO(app, cors_allowed_origins="http://localhost:5000")

@socketio.on("connect")
def handle_connect():
    app.logger.info("Player connected")

@socketio.on('join_room')
def handle_join_room(data):
    game_id = data['game_id']
    join_room(game_id)
    emit("joined_room", {"room": game_id})

@app.route("/", methods=["GET"])
def home():
    return app.send_static_file("index.html")

@app.route("/games", methods=["POST"])
def crete_game():
    while True: 
        lobby_id: str = str(uuid.uuid4())
        
        if not redis_client.exists(lobby_id):
            break

    settings = request.json

    lobby_data = {
        "state": WAITING,
        "players": [],
        "settings": settings.get("settings", {})
    }

    redis_client.set(lobby_id, json.dumps(lobby_data))

    app.logger.info(f"Player create lobby: {lobby_id}")

    return jsonify({"lobby_id": lobby_id}), 201

@app.route("/games/<lobby_id>/join", methods=["POST"])
def join_game(lobby_id):
    try:
        lobby_data = redis.get(lobby_id)
        player = request.json.get("player")
        lobby_data["players"].append(player)
        redis_client.set(lobby_id, json.dumps(lobby_data))
        
        socketio.emit("Player join", {"player": player}, room = lobby_id)

        return jsonify({"lobby_id": lobby_id}), 200
    except:
        return jsonify({}), 404

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
