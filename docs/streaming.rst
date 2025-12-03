Streaming
=========

Kafka
-----

.. code-block:: python

   AUDITTRAIL_STREAMING_ENABLED = True
   AUDITTRAIL_STREAM_PROVIDER = "audit_trail.streaming.kafka.KafkaPublisher"
   AUDITTRAIL_STREAM_CONFIG = {
       "topic": "audit-events",
       "bootstrap_servers": "broker01:9092,broker02:9092",
       "security.protocol": "SASL_SSL",
       "sasl.mechanisms": "PLAIN",
   }

Consumer example:

.. code-block:: python

   from confluent_kafka import Consumer

   consumer = Consumer({"bootstrap.servers": "broker01:9092", "group.id": "audit"})
   consumer.subscribe(["audit-events"])
   while True:
       msg = consumer.poll(1.0)
       if msg:
           print(msg.value())

Kinesis
-------

.. code-block:: python

   AUDITTRAIL_STREAMING_ENABLED = True
   AUDITTRAIL_STREAM_PROVIDER = "audit_trail.streaming.kinesis.KinesisPublisher"
   AUDITTRAIL_STREAM_CONFIG = {
       "stream": "audit-stream",
       "region": "us-east-1",
   }

IAM policy:

.. code-block:: json

   {
     "Effect": "Allow",
     "Action": ["kinesis:PutRecord", "kinesis:DescribeStream"],
     "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/audit-stream"
   }
