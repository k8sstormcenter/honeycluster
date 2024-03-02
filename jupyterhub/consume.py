!pip install pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import upper, col

# Create a Spark Session
spark = SparkSession.builder \
    .appName("KafkaReadTransformWriteToKafka") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

# Create a DataFrame that reads from the input Kafka topic name src-topic
df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "redpanda-src.redpanda.svc.cluster.local:9093")
    .option("subscribe", "tracessshpre")
    .load()
    .selectExpr("CAST(value AS STRING) as message")
)


import json
import tensorflow as tf
from confluent_kafka import Consumer, KafkaException

# Set up Kafka consumer
conf = {
    'bootstrap.servers': 'redpanda-src.redpanda.svc.cluster.local:9093',
    'group.id': 'mygroup',
    'auto.offset.reset': 'earliest',
}
consumer = Consumer(conf)

# Subscribe to the Kafka topic
consumer.subscribe(['tracessshpre'])

# Collect messages from Kafka
messages = []
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            break
        if msg.error():
            raise KafkaException(msg.error())
        else:
            # Parse message as JSON
            message = json.loads(msg.value().decode('utf-8'))
            # Filter messages with classification "baseline"
            if message.get('classification') == 'baseline':
                messages.append(message)
finally:
    consumer.close()

# Preprocess messages for TensorFlow
# This will depend on your specific use case
# For this example, let's assume each message is a dictionary with numeric values
data = [list(message.values()) for message in messages]
labels = ['baseline'] * len(data)

# Convert to TensorFlow Dataset
dataset = tf.data.Dataset.from_tensor_slices((data, labels))

# Now you can use `dataset` to train your TensorFlow model