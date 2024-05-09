package main

import (
	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	transform.OnRecordWritten(doTransform)
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Get the hash from the key and enclose it in quotes
	quote := []byte("\"")
	value := append(quote, e.Record().Key...)
	value = append(value, quote...)

	// Create a new record with the hash (old key) as the new key
	record := &transform.Record{
		Key:       nil,
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
