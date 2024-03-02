package main

import (
	"fmt"
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

	// Check if the counter has reached 200
	if counter >= 200 {
		return nil
	}

	// Get the key
	key := string(e.Record().Key)

	// Check if the key has been seen before
	if _, seen := keys[key]; !seen {
		// If the key has not been seen before, add it to the set and increment the counter
		keys[key] = struct{}{}
		counter++

		// Append the key to the CSV file
		//appendToCSV(key)
		fmt.Println(key)
	}

	return nil
}
