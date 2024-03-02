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

def decode_kafka_item(item):
    message = tf.io.decode_json_example(item.message)
    message['classification'] = tf.constant('baseline', dtype=tf.string)
    return message

BATCH_SIZE = 64
SHUFFLE_BUFFER_SIZE = 64



train_ds = tfio.IODataset.from_kafka('tetragon', partition=0, start=37790,stop=37794, servers='redpanda-src.redpanda.svc.cluster.local:9093')
train_ds = train_ds.shuffle(buffer_size=SHUFFLE_BUFFER_SIZE)
train_ds = train_ds.map(decode_kafka_item)
train_ds = train_ds.batch(BATCH_SIZE)


import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Input

# Define the number of input features
# This should match the number of features in your data
input_dim = len(train_ds.take(1))

# Define the encoding dimension
encoding_dim = 32

# Define the input layer
input_layer = Input(shape=(input_dim,))

# Define the encoder layer
encoder = Dense(encoding_dim, activation='relu')(input_layer)

# Define the decoder layer
decoder = Dense(input_dim, activation='sigmoid')(encoder)

# Create the autoencoder model
autoencoder = Model(inputs=input_layer, outputs=decoder)

# Compile the model
autoencoder.compile(optimizer='adam', loss='binary_crossentropy')

# Train the model
autoencoder.fit(train_ds, train_ds,
                epochs=50,
                batch_size=256,
                shuffle=True)