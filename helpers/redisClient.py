from redis.asyncio import Redis

redis_client = Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
)

STREAM = "capsule.jobs"
GROUP = "article-workers"
CONSUMER = "worker-1"


# class RedisClient:
#     async def queue_log(self, payload: dict):
#         await redis_client.lpush(
#             "capsule_processing",
#             json.dumps(payload),
#         )

#     async def publish_log(self, message: str):
#         await redis_client.publish(
#             channel,
#             message,
#         )
