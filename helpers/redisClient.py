import json
from typing import TYPE_CHECKING

from redis.asyncio import Redis

redis_client = Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)

channel = "capsule_logs"  # Redis channel for publishing capsule logs
image_channel = "capsule_images"  # Redis channel for publishing capsule images
if TYPE_CHECKING:
    image_message: str


class RedisClient:
    async def queue_log(self, payload: dict):
        await redis_client.lpush(
            "capsule_processing",
            json.dumps(payload),
        )

    async def publish_log(self, message: str):
        await redis_client.publish(
            channel,
            message,
        )
