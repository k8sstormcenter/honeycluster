package main

import (
	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	transform.OnRecordWritten(doTransform)
}

var value = []byte("null")

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Create a new record with null value
	record := &transform.Record{
		Key:       e.Record().Key,
		Value:     value,
		Offset:    e.Record().Offset,
		Timestamp: e.Record().Timestamp,
		Headers:   e.Record().Headers,
	}

	// Write the record to the destination topic
	err := w.Write(*record)
	if err != nil {
		return err
	}

	return nil
}
