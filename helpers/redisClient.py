from datetime import timezone
from importlib.metadata import files
from typing import TYPE_CHECKING
from redis import Redis

redis_client = Redis(
    host="localhost",
    port=6379,
    db=0,
    socket_timeout=10,
    socket_connect_timeout=10,
    decode_responses=True,
)

channel = "capsule_logs"  # Redis channel for publishing capsule logs
image_channel = "capsule_images"  # Redis channel for publishing capsule images
if TYPE_CHECKING:
    image_message: str


class RedisClient:
    """Redis client wrapper for managing Redis connections and operations."""

    async def connect(self):
        """Establish a connection to the Redis server."""
        try:
            await redis_client.ping()
            print("Connected to Redis server successfully.")
        except Exception as e:
            return f"Failed to connect to Redis server: {e}"

    async def publish(self, log_message: str, image_message: str):
        """Redis publisher for capsule logs"""
        receiver = redis_client.publish(
            channel, f"New capsule log entry: {log_message} | {timezone.now()}"
        )
        image_receiver = redis_client.publish(
            image_channel,
            f"New capsule image entry: {image_message} | {timezone.now()}",
        )
        return receiver, image_receiver

    async def subscribe(self):
        """Redis subscriber for capsule logs"""
        pubsub = redis_client.pubsub()
        pubsub.subscribe(channel)
        pubsub.subscribe(image_channel)

    async def close_connection(self):
        """Close the Redis connection."""
        redis_client.close()
        print("Redis connection closed.")
