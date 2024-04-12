package keys

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

var redpandaContainerId = "REDPANDA_CONTAINER_ID"

func hashString(s string) string {
	fmt.Println("Hashing string:", s)
	hash := sha256.Sum256([]byte(s))
	return hex.EncodeToString(hash[:])
}

var Baseline = []string{
	redpandaContainerId + "usrbinbashusrbinrpkclusterhealth",
	redpandaContainerId + "usrbincurlsilentfailkhttpredpandasrc0redpandasrcredpandasvcclusterlocal9644v1statusready",
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
	redpandaContainerId + "binbashcrpktopiccreatesmb",
	redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatesmb",
	redpandaContainerId + "usrbinbashusrbinrpktopiccreatesmb",
	redpandaContainerId + "optredpandalibexecrpktopiccreatesmb",
	redpandaContainerId + "binbashcmkdirptmpbaseline",
	redpandaContainerId + "usrbinmkdirptmpbaseline",
	redpandaContainerId + "usrbintestdtmpbaseline",
	redpandaContainerId + "usrbintarxmfCtmpbaseline",
}

// Create a new slice to hold the hashed keys
//var Baselinekeys = make([]string, len(Baseline))

// Iterate over Baselinekeys and hash each key
