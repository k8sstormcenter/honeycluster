### Getting into Rust - Experiment
export REDPANDA_VERSION=24.1.1

Please find the jq-binary under prebuilt/jq.wasm , you can then make it deploy your custom JQuery and stream it onto a new topic. Have fun!
![Custom JQ with precompiled jq.wasm](/docs/customJQ.png)

#### internal comments to self - can be used to reproduce my local seupt on MAC
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup target add wasm32-wasi
export REDPANDA_VERSION=24.1.1
export REDPANDA_CONSOLE_VERSION=2.5.2
rpk topic create src sort
rpk transform build
rpk transform deploy --var=FILTER='del(.email)' --input-topic=src --output-topic=sink

rpk transform deploy --var=FILTER='select(.process_kprobe.policy_name == "detect-symlinkat")' --input-topic=src --output-topic=sink
❯ rpk topic produce src

{"foo":42,"process_kprobe":{"policy_name":"detect-symlinkat"}, "email":"help@example.com"}


❯ rpk topic consume sink
{
  "topic": "sink",
  "value": "{\"email\":\"help@example.com\",\"foo\":42,\"process_kprobe\":{\"policy_name\":\"detect-symlinkat\"}}",
  "timestamp": 1714572728919,
  "partition": 0,
  "offset": 0
}

## -- now the real deal --


rpk transform deploy --var=FILTER='select(.process_kprobe.policy_name == "detect-symlinkat") | "\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])"' --input-topic=src --output-topic=sink


❯ rpk topic produce src


{"time": "2022-01-01T00:00:00Z", "process_kprobe": { "policy_name": "detect-symlinkat","process": {"pod": {"namespace": "default"},"binary": "/bin/bash","arguments": ["-c", "ls"]},"function_name": "kprobe_function","args": ["arg1", "arg2"]}}


❯ rpk topic consume sink
{
  "topic": "sink",
  "value": "\"2022-01-01T00:00:00Z detect-symlinkat  default kprobe_function /bin/bash [\\\"-c\\\",\\\"ls\\\"] arg1\"",
  "timestamp": 1714574300959,
  "partition": 0,
  "offset": 0
}