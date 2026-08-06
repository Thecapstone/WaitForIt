import json

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


# I would have liked to log out/print the contents of the raw_data
# It would help me understand how to efficiently work wih the data,
# If to access log description with bracket notation and push to a dictionary
# then finally feed in the article as the log.
# that would likely affect the structure of the article generation function.
# Food For Thought
# What is the likely output ot structure of the 'raw_data' content?
def process_queued_logs(queue_connection, queue_name):
    daily_logs = queue_connection.blpop(queue_name, timeout=10)

    if daily_logs:
        _queue_key, raw_data = daily_logs
        json.loads(raw_data)
