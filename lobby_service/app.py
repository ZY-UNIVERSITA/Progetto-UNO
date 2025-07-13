from flask import Flask, request, jsonify
import logging
import uuid
import redis
import json
from flask_socketio import SocketIO, join_room, emit
import jwt
import datetime
import jwt
import cryptography

WAITING: str = "waiting"
MIN_PLAYERS: int = 2

GAME_START_STREAM: str = "game_start_stream"

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

redis_client = redis.Redis(host="redis_service", port=6379, db=0)

socketio = SocketIO(app, cors_allowed_origins="http://127.0.0.1:5000")

print(cryptography.__version__)

def load_private_key(path='private_key.pem'):
    with open(path, 'r') as file:
        return file.read()

private_key = load_private_key()

@socketio.on("connect")
def handle_connect():
    app.logger.info("Player connected")

@socketio.on("join_room")
def handle_join_room(data):
    lobby_id = data["lobby_id"]
    join_room(lobby_id)

    lobby_data_raw = redis_client.get(lobby_id)
    lobby_data = json.loads(lobby_data_raw.decode("utf-8"))

    emit("player_joined", {"players": lobby_data["players"]}, room=lobby_id)

@socketio.on("start_game")
def handle_start_game(data):
    game_id = data["game_id"]
    emit("game_started", {"game_id": game_id}, room=game_id)

    try:
        lobby_data_raw = redis_client.get(game_id)
        redis_client.xadd(GAME_START_STREAM, { "payload": lobby_data_raw} )
    except Exception as e:
        app.logger.info(f"Error: {e}")


@app.route("/", methods=["GET"])
def home():
    return app.send_static_file("index.html")


@app.route("/games", methods=["POST"])
def crete_game():
    player = request.json.get("player")

    while True:
        lobby_id: str = str(uuid.uuid4())

        if not redis_client.exists(lobby_id):
            break

    settings = request.json

    lobby_data = {
        "lobby_id": lobby_id,
        "state": WAITING,
        "players": [ player ],
        "settings": settings.get("settings", {}),
    }

    redis_client.set(lobby_id, json.dumps(lobby_data))

    token = generate_token(player, lobby_id)

    app.logger.info(f"Player create lobby: {lobby_id}")

    return jsonify({"lobby_id": lobby_id, "token": token}), 201


@app.route("/games/<lobby_id>/join", methods=["POST"])
def join_game(lobby_id):
    try:
        lobby_data_raw = redis_client.get(lobby_id)
        lobby_data = json.loads(lobby_data_raw.decode("utf-8"))

        app.logger.info(f"Lobby info: {lobby_data}")

        player = request.json.get("player")
        lobby_data["players"].append(player)
        redis_client.set(lobby_id, json.dumps(lobby_data))

        token = generate_token(player, lobby_id)

        return jsonify({"lobby_id": lobby_id, "token": token}), 200
    except Exception as e:
        app.logger.info(f"Error: {e}")
        return jsonify({}), 500

def generate_token(username: str, lobby_id: str):
    payload = {
        "username": username,
        "lobby_id": lobby_id,
        "exp": datetime.datetime.now() + datetime.timedelta(minutes=30),
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")

    return token

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
