package main

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"sync"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

// var keys map[string]struct{}
var (
	keys = make(map[string]bool)
	mu   sync.Mutex
)

func main() {
	//keys = make(map[string]struct{})
	keys = make(map[string]bool)
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
var subFieldsToConcatenate = []string{"process.pod.container.id", "process.binary", "process.arguments"}

func createKey(incomingMessage map[string]interface{}) (string, string) {
	var keyParts []string
	//var pidInt int

	for _, topLevelField := range topLevelFields {
		if valtop, ok := incomingMessage[topLevelField].(map[string]interface{}); ok {
			value, ok := valtop["process"].(map[string]interface{})
			valpar, ok := valtop["parent"].(map[string]interface{})
			if !ok {
				return "", ""
			}

			containerID, _ := value["pod"].(map[string]interface{})["container"].(map[string]interface{})["id"].(string)
			binary, _ := value["binary"].(string)
			arguments, _ := value["arguments"].(string)
			pbinary, _ := valpar["binary"].(string)
			parguments, _ := valpar["arguments"].(string)

			keyParts = append(keyParts, containerID, binary, arguments, pbinary, parguments)

			//pid, ok := value["pid"].(float64) // JSON numbers are decoded as float64
			//if !ok {
			//	return "", ""
			//}

			//pidInt = int(pid) // Convert the pid to an integer
			//pidString := strconv.Itoa(pidInt)
			//pidString := fmt.Sprintf("%f", pid)

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
	// Check if the key has been seen before
	//if _, seen := keys[key]; !seen {
	//mu.Lock()
	//_, seen := keys[key]
	//if !seen {
	//	keys[key] = true
	record = NewRecord(finalkey, jsonData, e)
	//} else {
	//	record = NewRecord(key, jsonData, e)
	//}
	//mu.Unlock()

	err = w.Write(*record)
	if err != nil {
		return fmt.Errorf("failed to write record: %w", err)
	}

	return nil
}
