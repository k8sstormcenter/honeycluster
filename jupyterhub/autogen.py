!pip install tensorflow
!pip install tensorflow-io
!pip install kafka-python



import os
from datetime import datetime
import time
import threading
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
from sklearn.model_selection import train_test_split
import pandas as pd
import tensorflow as tf
import tensorflow_io as tfio





import tensorflow as tf
import tensorflow_io as tfio

# Define a function to decode the Kafka message and preprocess the data
def decode_kafka_item(item):
    message = tf.io.decode_json_example(item.message)
    # Preprocess the message here
    return message

# Read the data from Kafka
train_ds = tfio.IODataset.from_kafka('tetragon', partition=0, start=37790, stop=37794, servers='redpanda-src.redpanda.svc.cluster.local:9093')

# Decode and preprocess the data
train_ds = train_ds.map(decode_kafka_item)

# Batch the data
train_ds = train_ds.batch(BATCH_SIZE)


# Take one example from the dataset
example = next(iter(train_ds.take(1)))

# Determine the number of features based on the example
input_dim = len(example)
encoding_dim = 32
input_layer = Input(shape=(input_dim,))
encoder = Dense(encoding_dim, activation='relu')(input_layer)
decoder = Dense(input_dim, activation='sigmoid')(encoder)
autoencoder = Model(inputs=input_layer, outputs=decoder)

# Compile the model
autoencoder.compile(optimizer='adam', loss='binary_crossentropy')

# Train the model
autoencoder.fit(train_ds, train_ds, epochs=50, batch_size=256, shuffle=True)