package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/redpanda-data/redpanda/src/transform-sdk/go/transform"

	"os"
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

	return key
}

var keys = []string{
	"c10d19d2b73a8c20ce63966aa0982f7bd5a388567ce60edfea93367e7359154fbinshccurlsilentfailkhttp${SERVICE_NAME}redpandasrcredpandasvcclusterlocal9644v1statusready",
	"c10d19d2b73a8c20ce63966aa0982f7bd5a388567ce60edfea93367e7359154foptredpandalibexecrpkclusterhealth",
	"c10d19d2b73a8c20ce63966aa0982f7bd5a388567ce60edfea93367e7359154fusrbincurlsilentfailkhttpredpandasrc0redpandasrcredpandasvcclusterlocal9644v1statusready",
	"c10d19d2b73a8c20ce63966aa0982f7bd5a388567ce60edfea93367e7359154fusrbinbashusrbinrpkclusterhealth",
	"384af2687faf81d049c62c920e32a5cdf9d25080d5dd4ebae56e179f64372afbusrbinlsofnPEFfgi4i6",
	"5683e3edf0dc68d80faf7bdff90f0f4ec365c1c9460629eb986afaed72799f18usrbinlsofnPEFfgi4i6",
	"1389d1e44bd8ac130efd15bffefedca0c0d3aebba7da9d40030049710c6eea4dusrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherrke2charts675f1b63a0a83905972dcab2794479ed599a6f41b86cd6193d69472d0fa889c9resethard98e221e79a5c8461c48059d4e819b9325542cad7",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbinrancherhttplistenport80httpslistenport443auditlogpathvarlogauditlograncherapiauditlogauditlevel1auditlogmaxage1auditlogmaxbackup1auditlogmaxsize100nocacertshttplistenport80httpslistenport443addlocaltrue",
	"1389d1e44bd8ac130efd15bffefedca0c0d3aebba7da9d40030049710c6eea4dusrbingitccredentialhelperbinshcechopassword$GIT_PASSWORDCvarlibrancherdatalocalcatalogsv2ranchercharts4b40cac650031b74776e87c1a726b0484d0877c3ec137da0872547ff9b73a721resethardec2dc7135c87c3ef9f6eafca2e668367d50a3ffb",
	"1389d1e44bd8ac130efd15bffefedca0c0d3aebba7da9d40030049710c6eea4dusrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2ranchercharts4b40cac650031b74776e87c1a726b0484d0877c3ec137da0872547ff9b73a721resethardec2dc7135c87c3ef9f6eafca2e668367d50a3ffb",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2ranchercharts4b40cac650031b74776e87c1a726b0484d0877c3ec137da0872547ff9b73a721resethardec2dc7135c87c3ef9f6eafca2e668367d50a3ffb",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2ranchercharts4b40cac650031b74776e87c1a726b0484d0877c3ec137da0872547ff9b73a721resethardHEAD",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2ranchercharts4b40cac650031b74776e87c1a726b0484d0877c3ec137da0872547ff9b73a721revparseHEAD",
	"07f45afc9ea79ecb19d044d6e13dacddad0cbbecc66e82a4a5db6d519bdcf891usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2ranchercharts4b40cac650031b74776e87c1a726b0484d0877c3ec137da0872547ff9b73a721resethardec2dc7135c87c3ef9f6eafca2e668367d50a3ffb",
	"07f45afc9ea79ecb19d044d6e13dacddad0cbbecc66e82a4a5db6d519bdcf891usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherpartnercharts8f17acdce9bffd6e05a58a3798840e408c4ea71783381ecd2e9af30baad65974resethard5b498cba1c410428f26445b061a1a7a5741b9aa4",
	"07f45afc9ea79ecb19d044d6e13dacddad0cbbecc66e82a4a5db6d519bdcf891usrbinrancherhttplistenport80httpslistenport443auditlogpathvarlogauditlograncherapiauditlogauditlevel1auditlogmaxage1auditlogmaxbackup1auditlogmaxsize100nocacertshttplistenport80httpslistenport443addlocaltrue",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherpartnercharts8f17acdce9bffd6e05a58a3798840e408c4ea71783381ecd2e9af30baad65974resethard5b498cba1c410428f26445b061a1a7a5741b9aa4",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherpartnercharts8f17acdce9bffd6e05a58a3798840e408c4ea71783381ecd2e9af30baad65974resethardHEAD",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherpartnercharts8f17acdce9bffd6e05a58a3798840e408c4ea71783381ecd2e9af30baad65974revparseHEAD",
	"1389d1e44bd8ac130efd15bffefedca0c0d3aebba7da9d40030049710c6eea4dusrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherpartnercharts8f17acdce9bffd6e05a58a3798840e408c4ea71783381ecd2e9af30baad65974resethard5b498cba1c410428f26445b061a1a7a5741b9aa4",
	"07f45afc9ea79ecb19d044d6e13dacddad0cbbecc66e82a4a5db6d519bdcf891usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherrke2charts675f1b63a0a83905972dcab2794479ed599a6f41b86cd6193d69472d0fa889c9resethard98e221e79a5c8461c48059d4e819b9325542cad7",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherrke2charts675f1b63a0a83905972dcab2794479ed599a6f41b86cd6193d69472d0fa889c9resethard98e221e79a5c8461c48059d4e819b9325542cad7",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherrke2charts675f1b63a0a83905972dcab2794479ed599a6f41b86cd6193d69472d0fa889c9resethardHEAD",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherrke2charts675f1b63a0a83905972dcab2794479ed599a6f41b86cd6193d69472d0fa889c9revparseHEAD",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitccredentialhelperbinshcechopassword$GITPASSWORDCvarlibrancherdatalocalcatalogsv2rancherrke2charts675f1b63a0a83905972dcab2794479ed599a6f41b86cd6193d69472d0fa889c9revparseHEAD",
	"5683e3edf0dc68d80faf7bdff90f0f4ec365c1c9460629eb986afaed72799f18usrbindpkgqueryf${Package}${Version}",
	"5683e3edf0dc68d80faf7bdff90f0f4ec365c1c9460629eb986afaed72799f18usrbinunamesrio",
	"5683e3edf0dc68d80faf7bdff90f0f4ec365c1c9460629eb986afaed72799f18usrsbiniproute",
	"384af2687faf81d049c62c920e32a5cdf9d25080d5dd4ebae56e179f64372afbusrbindpkgqueryf${Package}${Version}",
	"384af2687faf81d049c62c920e32a5cdf9d25080d5dd4ebae56e179f64372afbusrbinunamesrio",
	"384af2687faf81d049c62c920e32a5cdf9d25080d5dd4ebae56e179f64372afbusrsbiniproute",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitCmanagementstatecatalogcachea67038d6110101d84b823470950db15b8ab6c06fe4e8895bcae7a337c1a8990drevparseHEAD",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitCmanagementstatecatalogcache380859f1003fe7603cddc6c15b34b7263f1f0deaa92ddcde465811d032ee7078revparseHEAD",
	"f955f18e1f4bfbc4e1d0bb9a8335352c1ea1ecee8f8e157377f36ca3013bfb79usrbingitCmanagementstatecatalogcachef341cfdfa521a9aa2b993cb34b26bb91b2d173ef1a7df8d41b8921b0e4f82788revparseHEAD",
	"6a183be3bb2f1d0d622697738dbc3aba682280a49a34a678fb5469875ec5c938usrbinsleep1h",
	"0a3508b6ca2ae17da09157c959e5ad2c8a2b7d121b124a285ff9d36b74399591usrbinsleep1h",
	"6a183be3bb2f1d0d622697738dbc3aba682280a49a34a678fb5469875ec5c938usrbinshcsleep1h",
	"0a3508b6ca2ae17da09157c959e5ad2c8a2b7d121b124a285ff9d36b74399591usrbinshcsleep1h",
	"e954f28fb0d61f96affc876906732e063ed845bca4ffd1a84b1881fc20ec9a85usrbinsleep1h",
}

var keysSet map[string]struct{}

func readCSV(filepath string) (map[string]struct{}, error) {
	// Open the file
	file, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	// Create a scanner to read the file
	scanner := bufio.NewScanner(file)

	// Read the keys into a set
	keys := make(map[string]struct{})
	for scanner.Scan() {
		keys[scanner.Text()] = struct{}{}
	}

	return keys, scanner.Err()
}

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
