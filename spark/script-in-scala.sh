# need to port forward http://spark-worker-0.spark-headless.spark.svc.cluster.local:4040/

#run this inside a spark pod
./bin/spark-shell --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2




import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

val spark = SparkSession.builder.appName("KafkaSparkStream").getOrCreate()

val df = spark
  .readStream
  .format("kafka")
  .option("kafka.bootstrap.servers", "redpanda-src.redpanda.svc.cluster.local:9093")
  .option("subscribe", "cr1")
  .load()

df.writeStream.foreachBatch { (batchDF: DataFrame, batchId: Long) => batchDF.orderBy(desc("timestamp")).show(5)}.start()