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

// doTransform is where you read the record that was written, and then you can
// output new records that will be written to the destination topic
func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	record := e.Record()
	if strings.Contains(string(record.Value), "kprobe") {
		return w.Write(record)
	}
	return nil
}
