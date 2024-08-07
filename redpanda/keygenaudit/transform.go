package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"regexp"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func main() {

	transform.OnRecordWritten(doTransform)
}

func NewRecord(key string, jsonData []byte, e transform.WriteEvent) *transform.Record {
	return &transform.Record{
		Key:       []byte(key),
		Value:     jsonData,
		Offset:    e.Record().Offset,
		Timestamp: e.Record().Timestamp,
		Headers:   e.Record().Headers,
	}
}

func removeTimestamps(data map[string]interface{}) {
	timestampRegex := regexp.MustCompile(`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z`)
	for key, value := range data {
		switch v := value.(type) {
		case map[string]interface{}:
			removeTimestamps(v)
		case string:
			if timestampRegex.MatchString(v) {
				delete(data, key)
			}
		case []interface{}:
			for i, item := range v {
				if itemMap, ok := item.(map[string]interface{}); ok {
					removeTimestamps(itemMap)
				} else if itemStr, ok := item.(string); ok {
					if timestampRegex.MatchString(itemStr) {
						v[i] = ""
					}
				}
			}
		}
	}
}

func createKey(incomingMessage map[string]interface{}) string {
	// Check if the "annotations" key exists
	//if _, ok := incomingMessage["annotations"]; !ok {
	//		return ""
	//}

	// Remove timestamps
	removeTimestamps(incomingMessage)

	// Convert the cleaned map back to JSON string
	cleanedJSON, err := json.Marshal(incomingMessage)
	if err != nil {
		return ""
	}

	// Create a hash
	hash := sha256.Sum256(cleanedJSON)
	return hex.EncodeToString(hash[:])
}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	var incomingMessage map[string]interface{}
	err := json.Unmarshal(e.Record().Value, &incomingMessage)
	if err != nil {
		return fmt.Errorf("failed to unmarshal incoming message: %w", err)
	}

	key := createKey(incomingMessage)

	finalkey := key

	jsonData, err := json.Marshal(incomingMessage)
	if err != nil {
		return fmt.Errorf("failed to marshal incoming message: %w", err)
	}
	var record *transform.Record

	record = NewRecord(finalkey, jsonData, e)

	err = w.Write(*record)
	if err != nil {
		return fmt.Errorf("failed to write record: %w", err)
	}

	return nil
}
