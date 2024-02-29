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
	keysSet = make(map[string]struct{}, len(keys))
	for _, key := range keys {
		keysSet[key] = struct{}{}
	}
	transform.OnRecordWritten(doTransform)
}

type Message struct {
	Timestamp string                 `json:"timestamp"`
	Data      map[string]interface{} `json:",inline"`
}

// To create the "hash" of a known message, focused on avoiding false negatives

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

var keys = []string{
	"b7c7da62ea3fab64db4f33feb4ad6182348ff0c1c4159f8aca2b259f7bd3bfddusrbinbashusrbinrpkclusterhealth",
	"b7c7da62ea3fab64db4f33feb4ad6182348ff0c1c4159f8aca2b259f7bd3bfddoptredpandalibexecrpkclusterhealth",
	"1084e9dc0195a860dc6da5b2d14ef5940ec4b6535ae515bffa5e468007f210afappcmdwebhookwebhookv2secureport10250dynamicservingcasecretnamespacecertmanagerdynamicservingcasecretnamecertmanagerwebhookcadynamicservingdnsnamescertmanagerwebhookdynamicservingdnsnamescertmanagerwebhookcertmanagerdynamicservingdnsnamescertmanagerwebhookcertmanagersvc",
	"d2887476a6ce0112fc768cd181440c0c8244dadcde20401faa8e50096b954167appconsoleconfigfilepathetcconsoleconfigsconfigyaml",
}

var keysSet map[string]struct{}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Unmarshal the incoming message into a map
	record := e.Record()
	if strings.Contains(string(record.Value), "/var/lib/rancher-data/local-catalogs/v2/rancher") {
		return nil
	}

	var incomingMessage map[string]interface{}
	err := json.Unmarshal(e.Record().Value, &incomingMessage)
	if err != nil {
		return err
	}

	// Extract 3 fields from the JSON and concat them as key
	key := createKey(incomingMessage)

	// Check if the key is in the CSV keys
	if _, ok := keysSet[key]; !ok {
		// If the key is not in the CSV keys, write the message

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
	}

	return nil
}
