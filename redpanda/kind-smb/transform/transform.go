package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"
)

func hashString(s string) string {
	hash := sha256.Sum256([]byte(s))
	return hex.EncodeToString(hash[:])
}

func hashMap(vs []string, f func(string) string) []string {
	vsm := make([]string, len(vs))
	for i, v := range vs {
		vsm[i] = f(v)
	}
	return vsm
}

func main() {

	var redpandaContainerId = "REDPANDA_CONTAINER_ID"

	var baselinekeys = []string{
		redpandaContainerId + "bincurlsilentfailkm5httpredpandasrc0redpandasrcredpandasvcclusterlocal9644v1statusready",
		redpandaContainerId + "binshccurlsilentfailkm5http{SERVICENAME}redpandasrcredpandasvcclusterlocal9644v1statusready",
		redpandaContainerId + "usrbinbashusrbinrpkclusterhealth",
		redpandaContainerId + "usrbincurlsilentfailkhttpredpandasrc0redpandasrcredpandasvcclusterlocal9644v1statusready",
		redpandaContainerId + "usrbincurlsilentfailkm5httpredpandasrc0redpandasrcredpandasvcclusterlocal9644v1statusready",
		redpandaContainerId + "binshccurlsilentfailkhttp{SERVICE_NAME}redpandasrcredpandasvcclusterlocal9644v1statusready",
		redpandaContainerId + "binshccurlsilentfailkhttp{SERVICENAME}redpandasrcredpandasvcclusterlocal9644v1statusready",
		redpandaContainerId + "optredpandalibexecrpkclusterhealth",
		redpandaContainerId + "binbashcrpktopiccreateextractcsv",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreateextractcsv",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreateextractcsv",
		redpandaContainerId + "optredpandalibexecrpktopiccreateextractcsv",
		redpandaContainerId + "binbashcrpktopiccreatebaseline",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatebaseline",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatebaseline",
		redpandaContainerId + "optredpandalibexecrpktopiccreatebaseline",
		redpandaContainerId + "binbashcrpktopiccreatesignalminusbaseline",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatesignalminusbaseline",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatesignalminusbaseline",
		redpandaContainerId + "optredpandalibexecrpktopiccreatesignalminusbaseline",
		redpandaContainerId + "binbashcrpktopiccreatetetragon",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatetetragon",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatetetragon",
		redpandaContainerId + "optredpandalibexecrpktopiccreatetetragon",
		redpandaContainerId + "binbashcrpktopiccreatekind-smb",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatekind-smb",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatekind-smb",
		redpandaContainerId + "optredpandalibexecrpktopiccreatekind-smb",
		redpandaContainerId + "binbashcmkdirptmpbaseline",
		redpandaContainerId + "usrbinmkdirptmpbaseline",
		redpandaContainerId + "usrbintestdtmpbaseline",
		redpandaContainerId + "usrbintarxmfCtmpbaseline",
		redpandaContainerId + "binbashcrpktopiccreatesmb",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatesmb",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatesmb",
		redpandaContainerId + "optredpandalibexecrpktopiccreatesmb",
		redpandaContainerId + "binbashcrpktopiccreatetracessshpre",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatetracessshpre",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatetracessshpre",
		redpandaContainerId + "optredpandalibexecrpktopiccreatetracessshpre",
		redpandaContainerId + "binbashcrpktopiccreatetracesssh",
		redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatetracesssh",
		redpandaContainerId + "usrbinbashusrbinrpktopiccreatetracesssh",
		redpandaContainerId + "optredpandalibexecrpktopiccreatetracesssh",
		redpandaContainerId + "binbashcmkdirptmptracessshpre",
		redpandaContainerId + "usrbinmkdirptmptracessshpre",
		redpandaContainerId + "usrbintestdtmptracessshpre",
		redpandaContainerId + "usrbintarxmfCtmptracessshpre",
		redpandaContainerId + "binbashcmkdirptmptracesssh",
		redpandaContainerId + "usrbinmkdirptmptracesssh",
		redpandaContainerId + "usrbintestdtmptracesssh",
		redpandaContainerId + "usrbintarxmfCtmptracesssh",
		redpandaContainerId + "binbashccdtmptracessshprerpktransformdeploy",
		redpandaContainerId + "usrbinrpkbashusrbinrpktransformdeploy",
		redpandaContainerId + "usrbinbashusrbinrpktransformdeploy",
		redpandaContainerId + "optredpandalibexecrpktransformdeploy",
		redpandaContainerId + "binbashccdtmptracessshrpktransformdeploy",
	}

	bkeys := hashMap(baselinekeys, hashString)
	// Register your transform function.
	// This is a good place to perform other setup too.
	keysSet = make(map[string]struct{}, len(bkeys))
	for _, key := range bkeys {
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
	key = strings.ReplaceAll(key, "\" ", "")
	key = strings.ReplaceAll(key, "-", "")
	key = strings.ReplaceAll(key, "/", "")
	key = strings.ReplaceAll(key, "=", "")
	key = strings.ReplaceAll(key, ".", "")
	key = strings.ReplaceAll(key, "containerd", "")
	key = strings.ReplaceAll(key, ":", "")
	key = strings.ReplaceAll(key, "+", "")
	key = strings.ReplaceAll(key, "$", "")
	key = strings.ReplaceAll(key, "_", "")
	key = strings.ReplaceAll(key, "&", "")

	hash := sha256.Sum256([]byte(key))
	return hex.EncodeToString(hash[:])
}

var keysSet map[string]struct{}

func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
	// Unmarshal the incoming message into a map
	record := e.Record()
	// Remove baseline where the hashes dont work:
	// Example of a very generic filter for changing containerIDs (like something involving git)
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

	// Check if the key is in the baseline table of hashes
	if _, ok := keysSet[key]; !ok {
		// If the key is not in the baseline (is not known), write the message

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
