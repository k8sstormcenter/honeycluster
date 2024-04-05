package main

import (
	"sync"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

var counter int
var keys map[string]struct{}
var lock sync.Mutex

func main() {
	// Initialize the counter and the set
	counter = 0
	keys = make(map[string]struct{})

	// Register the transform function
	transform.OnRecordWritten(doTransform)
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Lock the counter and the set
	lock.Lock()
	defer lock.Unlock()

	// Get the key
	key := string(e.Record().Key)

	// Check if the key has been seen before
	if _, seen := keys[key]; !seen {
		// If the key has not been seen before, add it to the set and increment the counter
		keys[key] = struct{}{}
		counter++

		// Create a new record with the JSON data
		record := &transform.Record{
			Key:       []byte(key),
			Value:     e.Record().Value,
			Offset:    e.Record().Offset,
			Timestamp: e.Record().Timestamp,
			Headers:   e.Record().Headers,
		}

		// Write the record to the destination topic
		w.Write(*record)

	}

	return nil
}
