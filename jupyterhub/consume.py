!pip install confluent_kafka
from confluent_kafka import Consumer, KafkaException

c = Consumer({
    'bootstrap.servers': 'redpanda-src.redpanda.svc.cluster.local:9093',
    'group.id': 'mygroup',
    'auto.offset.reset': 'earliest'
})

c.subscribe(['cr1'])

try:
    for _ in range(5):
        msg = c.poll(1.0)  # Wait for up to 1.0 seconds for a message
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        else:
            # Proper message
            print('Received message: {}'.format(msg.value().decode('utf-8')))

except KeyboardInterrupt:
    pass

finally:
    c.close()


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
    .option("subscribe", "cr1")
    .load()
    .selectExpr("CAST(value AS STRING) as message")
)

# Filter the DataFrame to select only those messages that contain the word "policy_name"
filtered_df = df.filter(col("message").contains("policy_name"))

# Write the filtered messages to the "tetragon" Kafka topic
query = (
    filtered_df
    .selectExpr("CAST(message AS STRING) AS value")
    .writeStream.format("kafka")
    .option("kafka.bootstrap.servers", "redpanda-src.redpanda.svc.cluster.local:9093")
    .option("topic", "tetragon")
    .option("checkpointLocation", "checkpoint_folder")  # Specify the checkpoint location
    .start()
)

query.awaitTermination()
