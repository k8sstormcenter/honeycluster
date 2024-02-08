import org.apache.spark.streaming._
import org.apache.spark.streaming.kafka010._
import org.apache.kafka.common.serialization.StringDeserializer

val sparkConf = new SparkConf().setAppName("KafkaSparkStream")
val ssc = new StreamingContext(sparkConf, Seconds(1))

val kafkaParams = Map[String, Object](
  "bootstrap.servers" -> "kafka:9092", // replace with your Kafka service address
  "key.deserializer" -> classOf[StringDeserializer],
  "value.deserializer" -> classOf[StringDeserializer],
  "group.id" -> "spark",
  "auto.offset.reset" -> "latest",
  "enable.auto.commit" -> (false: java.lang.Boolean)
)

val topics = Array("myTopic") // replace with your Kafka topic
val stream = KafkaUtils.createDirectStream[String, String](
  ssc,
  LocationStrategies.PreferConsistent,
  ConsumerStrategies.Subscribe[String, String](topics, kafkaParams)
)

// Perform your data analysis here...

ssc.start()
ssc.awaitTermination()