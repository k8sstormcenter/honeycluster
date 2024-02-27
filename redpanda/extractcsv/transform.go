package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
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

func appendToCSV(key string) {
	// Define the path to the CSV file
	path := "/tmp/extract/keys.csv"

	// Create the directory
	dir := filepath.Dir(path)
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		os.MkdirAll(dir, 0755)
	}

	// Open the CSV file
	file, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	// Create a CSV writer
	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write the key to the CSV file
	writer.Write([]string{key})
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
