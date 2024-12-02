NAME ?= honeycluster
CLUSTER_NAME := $(NAME)
HELM = $(shell which helm)

OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m | sed 's/x86_64/amd64/')


.EXPORT_ALL_VARIABLES:

##@ If you are on kind , first create the cluster with `make cluster-up` and then run `make honey-up`

##@ Scenario

.PHONY: honey-up
honey-up: tetragon-install vector redis traces  mongo  stixviz#k8spin tracee



##@ remove all honeycluster instrumentation from k8s
.PHONY: honey-down
honey-down: traces-off  wipe

.PHONY: wipe
wipe: 
	-$(HELM) uninstall tracee -n tracee
	- kubectl delete namespace tracee
	-$(HELM) uninstall mongo -n mongo
	- kubectl delete namespace mongo
	-$(HELM) uninstall vector -n vector
	- kubectl delete namespace vector
	-$(HELM) uninstall -n redpanda redis
	- kubectl delete namespace redpanda
	-$(HELM) uninstall tetragon -n kube-system


##@ Kind

.PHONY: cluster-up
cluster-up: kind ## Create the kind cluster
	$(KIND) create cluster --name $(CLUSTER_NAME) 
	-$(HELM) repo add jetstack https://charts.jetstack.io
	-$(HELM) repo update
	-$(HELM) upgrade --install cert-manager jetstack/cert-manager --set installCRDs=true --namespace cert-manager  --create-namespace

.PHONY: cluster-down
cluster-down: kind  ## Delete the kind cluster
	$(KIND) delete cluster --name $(CLUSTER_NAME)


.PHONY: k8spin
k8spin:
	-$(HELM) repo add kwasm http://kwasm.sh/kwasm-operator/
	-$(HELM) repo update
	-$(HELM) upgrade --install kwasm-operator kwasm/kwasm-operator --namespace kwasm --create-namespace --set kwasmOperator.installerImage=ghcr.io/spinkube/containerd-shim-spin/node-installer:v0.16.0
	-kubectl annotate node --all kwasm.sh/kwasm-node=true

.PHONY: stixviz
stixviz:
	-kubectl apply -f test/cti-stix-visualizer.yaml

.PHONY: tracee
tracee:
	-$(HELM) repo add aqua https://aquasecurity.github.io/helm-charts/
	-$(HELM) repo update
	-$(HELM) upgrade --install tracee aqua/tracee --namespace tracee --create-namespace

.PHONY: mongo	
mongo:
	-$(HELM) repo add bitnami https://charts.bitnami.com/bitnami
	-$(HELM) repo update
	-$(HELM) upgrade --install mongo bitnami/mongodb --namespace mongo --create-namespace --values mongo/values.yaml

## curretly candidate #1 for the network observability 
.PHONY: pixie
pixie:
	px deploy kubernetes

## kshark is useful if youre running in a high-stakes environment and you want pcaps
.PHONY: kshark
kshark:
	-$(HELM) repo add kubeshark https://helm.kubeshark.co
	-$(HELM) repo update
	-$(HELM) upgrade --install kubeshark kubeshark/kubeshark --create-namespace --namespace kubeshark --values kubeshark/values.yaml
	# kubectl port-forward service/kubeshark-front 8899:80



.PHONY: redis
redis:
	-$(HELM) repo add bitnami https://charts.bitnami.com/bitnami
	-$(HELM) repo update
	$(HELM) upgrade --install redis bitnami/redis -n redpanda --create-namespace --values redis/values.yaml



	
##@ Tetragon
.PHONY: tetragon-install
tetragon-install: helm check-context
	-$(HELM) repo add cilium https://helm.cilium.io
	-$(HELM) repo update
	-$(HELM) upgrade --install tetragon cilium/tetragon -n kube-system --values tetragon/values.yaml
	while [ "$$(kubectl -n kube-system get po -l app.kubernetes.io/name=tetragon -o jsonpath='{.items[0].metadata.generateName}')" != "tetragon-" ]; do \
		sleep 2; \
   	echo "Waiting for Tetragon pod to be created."; \
	done


.PHONY: vector
vector: helm 
	-$(HELM) repo add vector https://helm.vector.dev
	-$(HELM) upgrade --install vector vector/vector --namespace vector --create-namespace --values vector/gkevalues.yaml
	while [ "$$(kubectl -n vector get po -l app.kubernetes.io/name=vector -o jsonpath='{.items[0].metadata.generateName}')" != "vector-" ]; do \
		sleep 2; \
   	echo "Waiting for Vector pod to be created."; \
	done


.PHONY: traces
traces: 
	-kubectl apply -f traces/1sshd-probe-success.yaml
	-kubectl apply -f traces/1sshd-probe-spawnbash.yaml
	-kubectl apply -f traces/2enumerate-serviceaccount.yaml
	-kubectl apply -f traces/3enumerate-python.yaml
	-kubectl apply -f traces/4detect-scp-usage.yaml
	-kubectl apply -f traces/5detect-k8sapi-invoke.yaml
	-kubectl apply -f traces/6detect-symlinkat.yaml
	-kubectl apply -f traces/7detect-sensitivefile-access.yaml
	-kubectl apply -f traces/8detect-tcp.yaml
	-kubectl apply -f traces/9managed-identitytokenaccess.yaml
	-kubectl apply -f traces/10network-metadata.yaml

.PHONY: traces-off
traces-off: 
	-kubectl delete -f traces/1sshd-probe-success.yaml
	-kubectl delete -f traces/1sshd-probe-spawnbash.yaml
	-kubectl delete -f traces/2enumerate-serviceaccount.yaml
	-kubectl delete -f traces/3enumerate-python.yaml
	-kubectl delete -f traces/4detect-scp-usage.yaml
	-kubectl delete -f traces/5detect-k8sapi-invoke.yaml
	-kubectl delete -f traces/6detect-symlinkat.yaml
	-kubectl delete -f traces/7detect-sensitivefile-access.yaml
	-kubectl delete -f traces/8detect-tcp.yaml



##@ Tools

.PHONY: kind
KIND = $(shell pwd)/bin/kind
kind: ## Download kind if required
ifeq (,$(wildcard $(KIND)))
ifeq (,$(shell which kind 2> /dev/null))
	@{ \
		mkdir -p $(dir $(KIND)); \
		curl -sSLo $(KIND) https://kind.sigs.k8s.io/dl/$(KIND_VERSION)/kind-$(OS)-$(ARCH); \
		chmod + $(KIND); \
	}
else
KIND = $(shell which kind)
endif
endif

.PHONY: helm
HELM = $(shell pwd)/bin/helm
helm: ## Download helm if required
ifeq (,$(wildcard $(HELM)))
ifeq (,$(shell which helm 2> /dev/null))
	@{ \
		mkdir -p $(dir $(HELM)); \
		curl -sSLo $(HELM).tar.gz https://get.helm.sh/helm-v$(HELM_VERSION)-$(OS)-$(ARCH).tar.gz; \
		tar -xzf $(HELM).tar.gz --one-top-level=$(dir $(HELM)) --strip-components=1; \
		chmod + $(HELM); \
	}
else
HELM = $(shell which helm)
endif
endif



.PHONY: check-context
check-context:
    CURRENT_CONTEXT:=$(shell kubectl config current-context) \
    if [ "$${CURRENT_CONTEXT}" != "kind-$${CLUSTER_NAME}" ]; then \
        echo "Error: kubectl context is not set to kind-$${CLUSTER_NAME}"; \
        exit 1; \
    fi
