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


policy_name_count = 0
successful_ssh_connection_count = 0

try:
    while True:
        msg = c.poll(1.0)  # Wait for up to 1.0 seconds for a message
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        else:
            # Proper message
            message = msg.value().decode('utf-8')
            if 'policy_name' in message:
                policy_name_count += 1
            if 'successful_ssh_connection' in message:
                successful_ssh_connection_count += 1

except KeyboardInterrupt:
    pass


finally:
    c.close()

print('Number of messages containing "policy_name":', policy_name_count)
print('Number of messages containing "successful_ssh_connection":', successful_ssh_connection_count)