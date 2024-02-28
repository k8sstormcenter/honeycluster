package main

import (
	"strings"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	// Register your transform function.
	// This is a good place to perform other setup too.
	transform.OnRecordWritten(doTransform)
}

func create(oldKey string) string {

	// Join the key parts with a separator
	newkey := strings.ReplaceAll(oldKey, "_", "")
	newkey = strings.ReplaceAll(newkey, "-", "")
	newkey = strings.ReplaceAll(newkey, "/", "")
	newkey = strings.ReplaceAll(newkey, "=", "")
	newkey = strings.ReplaceAll(newkey, ".", "")
	newkey = strings.ReplaceAll(newkey, "containerd", "")
	newkey = strings.ReplaceAll(newkey, ":", "")
	newkey = strings.ReplaceAll(newkey, "+", "")

	return newkey
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Unmarshal the incoming message into a map

	// Remove the time fields from the message
	//removeTimeFields(incomingMessage)
	// Extract 3 fields from the JSON and concat them as key

	newkey := createKey(string(e.Record().Key))

	// Create a new record with the JSON data
	record := &transform.Record{
		Key:       []byte(newkey),
		Value:     []byte(string(e.Record().Key)),
		Offset:    e.Record().Offset,
		Timestamp: e.Record().Timestamp,
		Headers:   e.Record().Headers,
	}

	// Write the record to the destination topic
	w.Write(*record)

	return nil
}
