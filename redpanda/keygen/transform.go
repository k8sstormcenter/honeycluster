package main

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
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

var topLevelFields = []string{"process_exec", "process_exit", "process_kprobe"}

func createKey(incomingMessage map[string]interface{}) (string, string) {
	var keyParts []string

	for _, topLevelField := range topLevelFields {
		if valtop, ok := incomingMessage[topLevelField].(map[string]interface{}); ok {

			containerID := ""
			binary := ""
			arguments := ""
			if value, ok := valtop["process"].(map[string]interface{}); ok {

				containerID, _ = value["pod"].(map[string]interface{})["container"].(map[string]interface{})["id"].(string)
				binary, _ = value["binary"].(string)
				arguments, _ = value["arguments"].(string)
			}

			pbinary := ""
			parguments := ""

			if valpar, ok := valtop["parent"].(map[string]interface{}); ok {
				pbinary, _ = valpar["binary"].(string)
				parguments, _ = valpar["arguments"].(string)
			}

			keyParts = append(keyParts, containerID, binary, arguments, pbinary, parguments)

			key := strings.Join(keyParts, "")
			hash := md5.Sum([]byte(key))
			top := topLevelField[8:12]

			return hex.EncodeToString(hash[:]), top
		}
	}

	return "", ""
}
func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	var incomingMessage map[string]interface{}
	err := json.Unmarshal(e.Record().Value, &incomingMessage)
	if err != nil {
		return fmt.Errorf("failed to unmarshal incoming message: %w", err)
	}

	key, top := createKey(incomingMessage)

	finalkey := top + key

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
