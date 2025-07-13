import redis
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logging.info("App started")

STREAM_NAME: str = "game_start_stream"
GROUP_NAME: str = "game_start_group"
CONSUMER_NAME = f"game_worker_{int(time.time())}"

redis_client = redis.Redis(host="redis_service", port=6379, db=0)

try:
    redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id=0, mkstream=True)
except redis.exceptions.ResponseError:
    pass

def process_game(data):
    data_json = json.loads(data)
    lobby_id = data_json['lobby_id']
    players = data_json['players']
    logging.info(f"Avvio partita per lobby {lobby_id} con giocatori {players}")

while True:
    messages = redis_client.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: '>'}, count=1, block=30000)
    for stream, msgs in messages:
        for msg_id, msg_data in msgs:
            logging.info("messages arrived")
            process_game(msg_data)
            redis_client.xack(STREAM_NAME, GROUP_NAME, msg_id)

