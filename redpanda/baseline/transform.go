package main

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	// Register your transform function.
	// This is a good place to perform other setup too.
	transform.OnRecordWritten(doTransform)
}



var fieldsToRemove = []string{"pid", "tid", "auid", "uid", "exec_id", "parent_exec_id"}

type Message struct {
	Timestamp string                 `json:"timestamp"`
	Data      map[string]interface{} `json:",inline"`
}

func removeTimeFields(obj interface{}) {
	switch v := obj.(type) {
	case map[string]interface{}:
		for key, value := range v {
			// If the key contains "time", delete it
			for _, field := range fieldsToRemove {
				if strings.EqualFold(key, field) {
					delete(v, key)
					break
				}
			}
			if strings.Contains(strings.ToLower(key), "time") {
				delete(v, key)
			} else {
				// If the value is a map or a slice, recursively remove time fields
				removeTimeFields(value)
			}
		}
	case []interface{}:
		for i := range v {
			removeTimeFields(v[i])
		}
	}
}

var topLevelFields = []string{"process_exec", "process_exit", "process_kprobe"}
var subFieldsToConcatenate = []string{"process.pod.container.id", "process.binary", "process.arguments"}

func createKey(incomingMessage map[string]interface{}) string {
	var keyParts []string

	for _, topLevelField := range topLevelFields {
		if value, ok := incomingMessage[topLevelField]; ok {
			// If the top-level field exists, traverse its subfields
			for _, subField := range subFieldsToConcatenate {
				// Split the subfield into parts
				parts := strings.Split(subField, ".")
				subValue := value.(map[string]interface{})
				for _, part := range parts {
					// Traverse the map
					if v, ok := subValue[part]; ok {
						// If the part exists, add it to the key parts
						switch v := v.(type) {
						case map[string]interface{}:
							subValue = v
						default:
							keyParts = append(keyParts, fmt.Sprint(v))
						}
					}
				}
			}
		}
	}

	// Join the key parts with a separator
	key := strings.Join(keyParts, "")
	// Remove all whitespaces and escape characters
	key = strings.ReplaceAll(key, " ", "")
	key = strings.ReplaceAll(key, "\\", "")
	key = strings.ReplaceAll(key, "/", "")
	key = strings.ReplaceAll(key, "\"", "")
	key = strings.ReplaceAll(key, "'", "")
	key = strings.ReplaceAll(key, "-", "")
	key = strings.ReplaceAll(key, "/", "")
	key = strings.ReplaceAll(key, "=", "")
	key = strings.ReplaceAll(key, ".", "")
	key = strings.ReplaceAll(key, "containerd", "")
	key = strings.ReplaceAll(key, ":", "")
	key = strings.ReplaceAll(key, "+", "")
	key = strings.ReplaceAll(key, "$", "")

	return key
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Unmarshal the incoming message into a map
	var incomingMessage map[string]interface{}
	err := json.Unmarshal(e.Record().Value, &incomingMessage)
	if err != nil {
		return err
	}

	// Remove the time fields from the message
	removeTimeFields(incomingMessage)
	// Extract 3 fields from the JSON and concat them as key
	key := createKey(incomingMessage)

	// Marshal the result back to JSON
	jsonData, err := json.Marshal(incomingMessage)
	if err != nil {
		return err
	}

	// Create a new record with the JSON data
	record := &transform.Record{
		Key:       []byte(key),
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

	return nil
}
