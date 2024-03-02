package main

import (
	"encoding/json"

	"github.com/itchyny/gojq"
	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	// Register your transform function.
	// This is a good place to perform other setup too.
	transform.OnRecordWritten(doTransform)
}

// doTransform is where you read the record that was written, and then you can
// output new records that will be written to the destination topic

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {

	// Unmarshal the incoming message into a map
	var incomingMessage map[string]interface{}
	err := json.Unmarshal(e.Record().Value, &incomingMessage)
	if err != nil {
		return err
	}

	// Create a new jq query
	query, err := gojq.Parse("select( .process_kprobe != null and  .process_kprobe.policy_name == \"enumerate-util\" )| .")
	if err != nil {
		return err
	}

	// Execute the jq query
	iter := query.Run(incomingMessage)
	for {
		v, ok := iter.Next()
		if !ok {
			break
		}
		if err, ok := v.(error); ok {
			return err
		}
		// Marshal the result back to JSON
		jsonData, err := json.Marshal(v)
		if err != nil {
			return err
		}

		// Create a new record with the JSON data
		record := &transform.Record{
			Key:       e.Record().Key,
			Value:     jsonData,
			Offset:    e.Record().Offset,
			Timestamp: e.Record().Timestamp,
			Headers:   e.Record().Headers,
		}
		// Write the record to the destination topic
		err = w.Write(*record)
		if err != nil {
			return err
		}
	}
	return nil
}
