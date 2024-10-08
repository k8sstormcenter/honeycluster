NAME ?= honeycluster
CLUSTER_NAME := $(NAME)
HELM = $(shell which helm)

OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m | sed 's/x86_64/amd64/')


# keygen: generates hash for every message
DIRS := keygen
TOPICS := signal cr1 keygen applogs traceapi traceenum tracek8sclient tracescp tracessh tracesymlink 



.EXPORT_ALL_VARIABLES:

##@ If you are on kind , first create the cluster with `make cluster-up` and then run `make honey-up`

##@ Scenario

.PHONY: honey-up
honey-up: tetragon-install redpanda vector redpanda-wasm-hosted redis redpanda-connect-baseline redpanda-connect traces

.PHONY: honey-signal
honey-signal: baseline-signal # redpanda-connect-mongo

##@ remove all honeycluster instrumentation from k8s
.PHONY: honey-down
honey-down: traces-off redpanda-topic-delete wipe

.PHONY: wipe
wipe: 
	- kubectl delete namespace ssh
	-$(HELM) uninstall vector -n vector
	- kubectl delete namespace vector
	-$(HELM) uninstall redpanda-src -n redpanda
	- kubectl delete -n redpanda pvc datadir-redpanda-src-0
	-$(HELM) uninstall -n redpanda redpanda-connect-baseline
	-$(HELM) uninstall -n redpanda redpanda-connect
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


##@ Redpanda
# useful:  alias internal-rpk="kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- rpk"
.PHONY: redpanda
redpanda: 
	-$(HELM) repo add redpanda-data https://charts.redpanda.com 
	-$(HELM) repo update
	-$(HELM) upgrade --install redpanda-src redpanda-data/redpanda --version 5.8.8 -n redpanda --create-namespace --values redpanda/diffvalues.yaml 
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create cr1" 
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create applogs" 


.PHONY: redpanda-wasm
redpanda-wasm:
	@for dir in $(DIRS); do \
		cd redpanda/$$dir/ && go mod tidy && rpk transform build && cd ../.. ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create $$dir" ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "mkdir -p /tmp/$$dir" ;\
		kubectl cp redpanda/$$dir/transform.yaml redpanda/redpanda-src-0:/tmp/$$dir/. ;\
		kubectl cp redpanda/$$dir/$$dir.wasm redpanda/redpanda-src-0:/tmp/$$dir/. ;\
		kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "cd /tmp/$$dir/ && rpk transform deploy" ;\
	done



.PHONY: redpanda-wasm-hosted
redpanda-wasm-hosted:	
	@for dir in $(DIRS); do \
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create $$dir" ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/$$dir.wasm --name $$dir --input-topic=$$(sed -n -e 's/^input-topic: *//p' redpanda/$$dir/transform.yaml) --output-topic=$$dir --var language=tinygo-no-goroutines " ;\
	done


.PHONY: redis
redis:
	-$(HELM) repo add bitnami https://charts.bitnami.com/bitnami
	-$(HELM) repo update
	$(HELM) upgrade --install redis bitnami/redis -n redpanda --create-namespace --values redis/values.yaml


##@ Filters out the hashes in the baseline from the keygen topic and writes result to signal
.PHONY: redpanda-connect
redpanda-connect:
	$(HELM) upgrade --install -n redpanda redpanda-connect ./redpanda/connect


.PHONY: redpanda-connect-mongo
redpanda-connect-mongo:
	cp redpanda/connect/configs-external/*.yaml redpanda/connect/configs/.
	$(HELM) upgrade --install -n redpanda redpanda-connect ./redpanda/connect

##@ Adds all hashes from the keygen topic to a set used to filter out messages for the signal topics
.PHONY: redpanda-connect-baseline
redpanda-connect-baseline:
	$(HELM) upgrade --install -n redpanda redpanda-connect-baseline --set connect.configs=baseline/*.yaml ./redpanda/connect


##@ Stops the population of the baseline topic
.PHONY: baseline-signal
baseline-signal:
	-$(HELM) uninstall -n redpanda redpanda-connect-baseline

	
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


# TODO : you need to copy paste the second cmd into your terminal, cant find the right combo of escape chars
.PHONY: redpanda-wasm-jq
redpanda-wasm-jq:	check-context
	kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create tracesymlink" 
	kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/jq.wasm --name tracesymlink --input-topic=signal --output-topic=tracesymlink --var language=rust  --var=FILTER='select(.process_kprobe.policy_name == \"detect-symlinkat\") | \"\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])\"'"

	kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create traceapi" 
	kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/jq.wasm --name traceapi --input-topic=signal --output-topic=traceapi --var language=rust  --var=FILTER='select(.process_kprobe != null and ( .process_kprobe.policy_name == \"k8s-api-call\" or .process_kprobe.policy_name == \"enumerate-service-account\" ))| \"\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])\"'"

	kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create traceenum" 
	kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/jq.wasm --name traceenum --input-topic=signal --output-topic=traceenum --var language=rust  --var=FILTER='select( .process_kprobe != null and  .process_kprobe.policy_name == \"enumerate-util\" )| \"\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])\"'"

	kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create tracek8sclient" 
	kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/jq.wasm --name tracek8sclient --input-topic=signal --output-topic=tracek8sclient --var language=rust  --var=FILTER='select( .process_kprobe != null and  .process_kprobe.policy_name == \"detect-k8sapi-invoke\" )| \"\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])\"'"

	kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create tracescp" 
	kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/jq.wasm --name tracescp --input-topic=signal --output-topic=tracescp --var language=rust  --var=FILTER='select( .process_kprobe.policy_name == \"detect-scp-usage\" ) | \"\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])\"'"

	kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create tracessh" 
	kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform deploy --file https://raw.githubusercontent.com/k8sstormcenter/honeycluster/main/prebuilt/jq.wasm --name tracessh --input-topic=signal --output-topic=tracessh --var language=rust  --var=FILTER='select( .process_kprobe != null and ( .process_kprobe.policy_name == \"ssh-spawn-bash\" or .process_kprobe.policy_name == \"successful-ssh-connections\" ))| \"\(.time) \(.process_kprobe.policy_name)  \(.process_kprobe.process.pod.namespace) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.args[])\"'"


.PHONY: redpanda-topic-delete
redpanda-topic-delete:
	@for topic in $(TOPICS); do \
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk transform delete --no-confirm $$topic" || true; \
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic delete $$topic" || true; \
	done


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

.PHONY: rpk
RPK = $(shell pwd)/bin/rpk
rpk: ## Download rpk if required
ifeq (,$(wildcard $(RPK)))
ifeq (,$(shell which rpk 2> /dev/null))
	@{ \
		mkdir -p $(dir $(RPK)); \
		curl -sSLo $(RPK).zip https://github.com/redpanda-data/redpanda/releases/latest/download/rpk-$(OS)-$(ARCH).zip; \
		unzip $(RPK).zip -d $(shell pwd)/bin; \
		rm $(RPK).zip; \
		chmod + $(RPK); \
	}
else
RPK = $(shell which rpk)
endif
endif

.PHONY: check-context
check-context:
    CURRENT_CONTEXT:=$(shell kubectl config current-context) \
    if [ "$${CURRENT_CONTEXT}" != "kind-$${CLUSTER_NAME}" ]; then \
        echo "Error: kubectl context is not set to kind-$${CLUSTER_NAME}"; \
        exit 1; \
    fi
