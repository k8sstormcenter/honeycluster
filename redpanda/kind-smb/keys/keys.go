package keys

import (
	"crypto/sha256"
	"encoding/hex"
)

func hashString(s string) string {
	hash := sha256.Sum256([]byte(s))
	return hex.EncodeToString(hash[:])
}

var redpandaContainerId = "REDPANDA_CONTAINER_ID"

var Baselinekeys = []string{
	hashString(redpandaContainerId + "usrbinbashusrbinrpkclusterhealth"),
	hashString(redpandaContainerId + "usrbincurlsilentfailkhttpredpandasrc0redpandasrcredpandasvcclusterlocal9644v1statusready"),
	hashString(redpandaContainerId + "binshccurlsilentfailkhttp{SERVICE_NAME}redpandasrcredpandasvcclusterlocal9644v1statusready"),
	hashString(redpandaContainerId + "binshccurlsilentfailkhttp{SERVICENAME}redpandasrcredpandasvcclusterlocal9644v1statusready"),
	hashString(redpandaContainerId + "optredpandalibexecrpkclusterhealth"),
	hashString(redpandaContainerId + "binbashcrpktopiccreateextractcsv"),
	hashString(redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreateextractcsv"),
	hashString(redpandaContainerId + "usrbinbashusrbinrpktopiccreateextractcsv"),
	hashString(redpandaContainerId + "optredpandalibexecrpktopiccreateextractcsv"),
	hashString(redpandaContainerId + "binbashcrpktopiccreatebaseline"),
	hashString(redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatebaseline"),
	hashString(redpandaContainerId + "usrbinbashusrbinrpktopiccreatebaseline"),
	hashString(redpandaContainerId + "optredpandalibexecrpktopiccreatebaseline"),
	hashString(redpandaContainerId + "binbashcrpktopiccreatesignalminusbaseline"),
	hashString(redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatesignalminusbaseline"),
	hashString(redpandaContainerId + "usrbinbashusrbinrpktopiccreatesignalminusbaseline"),
	hashString(redpandaContainerId + "optredpandalibexecrpktopiccreatesignalminusbaseline"),
	hashString(redpandaContainerId + "binbashcrpktopiccreatetetragon"),
	hashString(redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatetetragon"),
	hashString(redpandaContainerId + "usrbinbashusrbinrpktopiccreatetetragon"),
	hashString(redpandaContainerId + "optredpandalibexecrpktopiccreatetetragon"),
	hashString(redpandaContainerId + "binbashcrpktopiccreatekind-smb"),
	hashString(redpandaContainerId + "usrbinrpkbashusrbinrpktopiccreatekind-smb"),
	hashString(redpandaContainerId + "usrbinbashusrbinrpktopiccreatekind-smb"),
	hashString(redpandaContainerId + "optredpandalibexecrpktopiccreatekind-smb"),
	hashString(redpandaContainerId + "binbashcmkdirptmpbaseline"),
	hashString(redpandaContainerId + "usrbinmkdirptmpbaseline"),
	hashString(redpandaContainerId + "usrbintestdtmpbaseline"),
	hashString(redpandaContainerId + "usrbintarxmfCtmpbaseline"),
}
