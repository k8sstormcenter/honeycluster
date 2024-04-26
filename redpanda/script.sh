#!/bin/bash

internal-rpk  topic consume keygen -f '%k\n' > /tmp/list
sort -u /tmp/list  > /tmp/list.uniq
#sed -i 's/.*/"&",/' list.uniq  ## LINUX
sed -i '' 's/.*/"&",/' /tmp/list.uniq  ## MAC
paste -s -d ' ' /tmp/list.uniq >> one_line_list.txt
HASHLIST=$(cat one_line_list.txt )
sed "s/\$HASHLIST/$HASHLIST/g" signal/keyless/transform.go > signal/transform.go