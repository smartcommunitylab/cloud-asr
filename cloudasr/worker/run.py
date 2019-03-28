import os
from lib import create_worker

#os.environ['kafka_broker_url']="172.17.0.1:9092"
worker = create_worker(os.environ['MODEL'], os.environ['RECORDINGS_SAVER_ADDR'],os.environ['kafka_broker_url'])
worker.run()
