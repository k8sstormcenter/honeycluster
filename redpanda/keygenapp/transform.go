package main

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

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

func createKey(incomingMessage map[string]interface{}) string {
	var keyParts []string

	file := ""
	message := ""
	if value, ok := incomingMessage["file"].(string); ok {
		file = value
	}
	if value, ok := incomingMessage["message"].(string); ok {
		message = value
	}

	// Remove timestamp from message
	re := regexp.MustCompile(`time="[^"]+"|^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\+\d{4} `)
	cleanedMessage := re.ReplaceAllString(message, "")

	keyParts = append(keyParts, file, cleanedMessage)

	key := strings.Join(keyParts, "")
	hash := md5.Sum([]byte(key))

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
