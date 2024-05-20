package main

import (
	"strconv"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	transform.OnRecordWritten(doTransform)
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Unescape value
	value, _ := strconv.Unquote(string(e.Record().Value))

	// Create a new record with unescaped value
	record := &transform.Record{
		Key:       e.Record().Key,
		Value:     []byte(value),
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
