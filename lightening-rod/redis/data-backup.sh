redis-cli -h 127.0.0.1 -p 6379 LRANGE tetra 0 -1 | tr '\r' '\n' | sed 's/"//g' > output_tetra.csv
redis-cli -h 127.0.0.1 -p 6379 LRANGE falco 0 -1 | tr '\r' '\n' | sed 's/"//g' > output_falco.csv