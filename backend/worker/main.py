import time
import os
import redis
from rq import Worker, Queue

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')

if __name__ == '__main__':
    print("Worker starting up...")
    
    # Wait for Redis to be available
    r = redis.from_url(redis_url)
    while True:
        try:
            r.ping()
            print("Connected to Redis.")
            break
        except Exception:
            print("Waiting for Redis...")
            time.sleep(2)
            
    # Start RQ worker (rq >= 1.16: pass connection directly, no Connection context manager)
    queue_name = os.getenv("QUEUE_NAME", "default")
    print(f"Listening on queue: {queue_name}")
    
    queues = [Queue(queue_name, connection=r)]
    worker = Worker(queues, connection=r)
    worker.work()
