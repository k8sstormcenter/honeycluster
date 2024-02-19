package main

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/itchyny/gojq"
	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {
	// Register your transform function.
	// This is a good place to perform other setup too.

	transform.OnRecordWritten(doTransform)
}

var seenMessages = make(map[string]bool)
var fieldsToRemove = []string{"pid", "tid", "auid", "uid", "exec_id", "parent_exec_id"}

type Message struct {
	Timestamp string                 `json:"timestamp"`
	Data      map[string]interface{} `json:",inline"`
}

func removeTimeFields(obj map[string]interface{}) {
	for key, value := range obj {
		// If the key contains "time", delete it
		for _, field := range fieldsToRemove {
			if strings.EqualFold(key, field) {
				delete(obj, key)
				break
			}
		}
		if strings.Contains(strings.ToLower(key), "time") {
			delete(obj, key)
		} else {
			// If the value is a map, recursively remove time fields
			if subObj, ok := value.(map[string]interface{}); ok {
				removeTimeFields(subObj)
			}
		}
	}
}
func filterMessages(rawMessage []byte) bool {
	var message Message
	if err := json.Unmarshal(rawMessage, &message); err != nil {
		fmt.Println("Error unmarshalling JSON:", err)
		return false
	}

	// Remove the timestamp field and all other unique fields
	delete(message.Data, "time")
	removeTimeFields(message.Data)
	// Convert the JSON object back to a string for comparison
	messageString, err := json.Marshal(message.Data)
	if err != nil {
		fmt.Println("Error marshalling JSON:", err)
		return false
	}

	// Check if we've seen this message before
	if seenMessages[string(messageString)] {
		// This is a duplicate message, ignore it
		return false
	} else {
		// This is a new message, add it to the set and process it
		seenMessages[string(messageString)] = true
		return true
	}
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {

	// Unmarshal the incoming message into a map
	var incomingMessage map[string]interface{}
	err := json.Unmarshal(e.Record().Value, &incomingMessage)
	if err != nil {
		return err
	}

	// We want all record that are not from the following namespaces // .process_kprobe != null  " +
	query, err := gojq.Parse("select(  " +
		" .process_kprobe.process.pod.namespace != \"jupyter\"   " +
		"and .process_kprobe.process.pod.namespace != \"cert-manager\" " +
		"and .process_kprobe.process.pod.namespace != \"redpanda\" " +
		"and .process_kprobe.process.pod.namespace != \"spark\" " +
		"and .process_kprobe.process.pod.namespace != \"parseable\" " +
		"and .process_kprobe.process.pod.namespace != \"vector\" )| " +
		".")

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
		// Now check if the message is a duplicate
		if !filterMessages(jsonData) {

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
	}
	return nil
}
