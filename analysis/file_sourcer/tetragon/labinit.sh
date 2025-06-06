#!/bin/bash

#TODO: we need to map the different tetragon types into a superset schema else pixie cant deal with it

input_file="/honeycluster/analysis/file_sourcer/tetragon/example_tetragon_schema.json"
output_file="/tmp/tetragon.json"

mv $input_file $output_file