import redis
import json
import time

STREAM_NAME: str = "game_start_stream"
GROUP_NAME: str = "game_start_group"
CONSUMER_NAME = f"game_worker_{int(time.time())}"

redis_client = redis.Redis(host="redis_service", port=6379, db=0)

try:
    redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id=0, mkstream=True)
except redis.exceptions.ResponseError:
    pass

def process_game(data):
    lobby_id = data['lobby_id']
    players = json.loads(data['players'])
    print(f"Avvio partita per lobby {lobby_id} con giocatori {players}")

while True:
    messages = redis_client.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: '>'}, count=1, block=30000)
    for stream, msgs in messages:
        for msg_id, msg_data in msgs:
            process_game(msg_data)
            redis_client.xack(STREAM_NAME, GROUP_NAME, msg_id)

