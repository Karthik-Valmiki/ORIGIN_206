import redis
import os
from rq import Queue
from ..config import settings
import uuid

def get_redis_conn():
    return redis.from_url(settings.REDIS_URL)

def enqueue_inspection_job(inspection_id: uuid.UUID):
    conn = get_redis_conn()
    q = Queue(os.getenv("QUEUE_NAME", "default"), connection=conn)
    # the function to be called must be importable by the worker
    job = q.enqueue("worker.pipeline.process_inspection", str(inspection_id))
    return job.id
