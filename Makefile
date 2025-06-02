NAME ?= honeycluster
CLUSTER_NAME := $(NAME)
HELM = $(shell which helm)

CURRENT_CONTEXT := $(shell kubectl config current-context)
OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m | sed 's/x86_64/amd64/')
ifeq ($(findstring kind-,$(CURRENT_CONTEXT)),kind-)
    $(eval VALUES := values.yaml)
else ifeq ($(findstring Default,$(CURRENT_CONTEXT)),Default)
    $(eval VALUES := values_k0s.yaml)
else ifeq ($(findstring default,$(CURRENT_CONTEXT)),default)
    $(eval VALUES := values_k3s.yaml)
else
    $(eval VALUES := values_gke.yaml)
endif

.EXPORT_ALL_VARIABLES:

##@ If you are on kind , first create the cluster with `make cluster-up` and then run `make honey-up`

##@ Scenario

.PHONY: honey-up
honey-up: tetragon vector redis traces  lighteningrod stixviz kubescape tracee falco #k8spin mongo

.PHONY: dev
dev: cluster-up tetragon vector redis traces lighteningrod stixviz kubescape tracee falco dev-ui

.PHONY: k0s
k0s: storage cert-man tetragon vector redis patch traces kubescape dev-ui #pixie-cli pixie# add pixie here once you automated the auth0

.PHONY: bob
bob: storage kubescape-bob #tetragon vector redis patch traces 

.PHONY: bob-talos
bob-talos: kubescape-bob-kind selinux-override

##@ remove all honeycluster instrumentation from k8s
.PHONY: honey-down
honey-down: traces-off  wipe

.PHONY: wipe
wipe: 
	-$(HELM) uninstall tracee -n honey
	- kubectl delete -f lightening-rod/cti-stix-visualizer-deployment.yaml 
	- kubectl delete -f lightening-rod/deployment.yaml
	-$(HELM) uninstall mongo -n honey
	-$(HELM) uninstall vector -n honey
	-$(HELM) uninstall kubescape -n honey
	-$(HELM) uninstall falco -n honey
	-$(HELM) uninstall tracee -n honey
	-$(HELM) uninstall deepfence-console --namespace honey
	- kubectl delete pvc file-server-deepfence-console-file-server-0 -n honey 
	- kubectl delete pvc kafka-broker-deepfence-console-kafka-broker-0 -n honey
	- kubectl delete pvc neo4j-deepfence-console-neo4j-0 -n honey
	- kubectl delete pvc postgres-deepfence-console-postgres-0 -n honey 
	- kubectl delete pvc redis-deepfence-console-redis-0 -n honey
	- kubectl delete namespace honey
	-$(HELM) uninstall -n storm redis
	- kubectl delete namespace storm
	- kubectl delete namespace lightening
	-$(HELM) uninstall tetragon -n honey


##@ Kind

.PHONY: cluster-up
cluster-up: kind ## Create the kind cluster
	$(KIND) create cluster --name $(CLUSTER_NAME)  

.PHONY: cert-man
cert-man:
	-$(HELM) repo add jetstack https://charts.jetstack.io
	-$(HELM) repo update
	-$(HELM) upgrade --install cert-manager jetstack/cert-manager --set installCRDs=true --namespace cert-manager  --create-namespace

.PHONY: cluster-down
cluster-down: kind  ## Delete the kind cluster
	$(KIND) delete cluster --name $(CLUSTER_NAME)


.PHONY: kind-pixie-up
kind-pixie-up: 
	$(KIND) create cluster --name pixie-cloud 
	-$(HELM) repo add jetstack https://charts.jetstack.io
	-$(HELM) repo update
	-$(HELM) upgrade --install cert-manager jetstack/cert-manager --set installCRDs=true --namespace cert-manager  --create-namespace


.PHONY: storage
storage:
	kubectl apply -f https://openebs.github.io/charts/openebs-operator-lite.yaml
	kubectl apply -f https://openebs.github.io/charts/openebs-lite-sc.yaml
	kubectl apply -f honeystack/openebs/sc.yaml
	kubectl patch storageclass local-hostpath -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
	
.PHONY: patch
patch:	
	kubectl patch pvc redis-data-redis-master-0 -n storm -p '{"spec": {"storageClassName": "local-hostpath"}}'


.PHONY: pixie-cloud
pixie-cloud:
	-kubectl config use-context kind-pixie-cloud
	cd ../pixie/
	-kubectl create namespace plc
	-./scripts/create_cloud_secrets.sh
	-kustomize build k8s/cloud_deps/base/elastic/operator | kubectl apply -f -
	-kustomize build k8s/cloud_deps/public | kubectl apply -f -
	-kustomize build k8s/cloud/public/ | kubectl apply -f -

	
.PHONY: k8spin
k8spin:
	-$(HELM) repo add kwasm http://kwasm.sh/kwasm-operator/
	-$(HELM) repo update
	-$(HELM) upgrade --install kwasm-operator kwasm/kwasm-operator --namespace storm --create-namespace --set kwasmOperator.installerImage=ghcr.io/spinkube/containerd-shim-spin/node-installer:v0.16.0
	-kubectl annotate node --all kwasm.sh/kwasm-node=true

.PHONY: stixviz
stixviz:
	-kubectl apply -f lightening-rod/cti-stix-visualizer-deployment.yaml 
	
.PHONY: lighteningrod
lighteningrod:
	-kubectl apply -f lightening-rod/deployment.yaml	

.PHONY: dev-ui
dev-ui:
	-kubectl apply -f development/redis-insight.yaml

.PHONY: falco
falco:
	-$(HELM) repo add falcosecurity https://falcosecurity.github.io/charts
	-$(HELM) repo update
	-$(HELM) upgrade --install falco falcosecurity/falco --namespace honey --create-namespace --values honeystack/falco/values.yaml		



.PHONY: tracee
tracee:
	-$(HELM) repo add aqua https://aquasecurity.github.io/helm-charts/
	-$(HELM) repo update
	-$(HELM) upgrade --install tracee aqua/tracee --namespace honey --create-namespace

.PHONY: mongo	
mongo:
	-$(HELM) repo add bitnami https://charts.bitnami.com/bitnami
	-$(HELM) repo update
	-$(HELM) upgrade --install mongo bitnami/mongodb --namespace honey --create-namespace --values honeystack/mongo/values.yaml

.PHONY: kubescape
kubescape:
	-$(HELM) repo add kubescape https://kubescape.github.io/helm-charts/
	-$(HELM) repo update
	$(HELM) upgrade --install kubescape kubescape/kubescape-operator -n honey --create-namespace --values honeystack/kubescape/$(VALUES)

.PHONY: kubescape-bob-kind
kubescape-bob-kind:
	-$(HELM) repo add kubescape https://kubescape.github.io/helm-charts/
	-$(HELM) repo update
	$(HELM) upgrade --install kubescape kubescape/kubescape-operator -n honey --values honeystack/kubescape/values_bob_kind.yaml --create-namespace
	kubectl apply -f honeystack/kubescape/runtimerules.yaml
	kubectl apply -f honeystack/kubescape/kscloudconfig.yaml
	sleep 10
	kubectl rollout restart -n honey ds node-agent


.PHONY: webapp-bob-kind
webapp-bob-kind:
	kubectl apply -f traces/kubescape-verify/attacks/webapp/webapp_debug_kind.yaml
	kubectl wait --for=condition=Available deployment/webapp 

.PHONY: selinux-override
selinux-override:
	kubectl label namespace openebs pod-security.kubernetes.io/enforce=privileged --overwrite
	kubectl label namespace honey pod-security.kubernetes.io/enforce=privileged --overwrite
	kubectl patch ds node-agent -n honey --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/securityContext/seccompProfile", "value": {"type": "RuntimeDefault"}}]'
	

# These values are for k0s until the Inspector Gadget PR is merged, as we need to override the socket path
.PHONY: kubescape-bob
kubescape-bob:
	-$(HELM) repo add kubescape https://kubescape.github.io/helm-charts/
	-$(HELM) repo update
	$(HELM) upgrade --install kubescape kubescape/kubescape-operator -n honey --values honeystack/kubescape/values_bob.yaml --create-namespace
	kubectl apply -f honeystack/kubescape/runtimerules.yaml
	kubectl apply -f honeystack/kubescape/kscloudconfig.yaml
	sleep 10
	kubectl rollout restart -n honey ds node-agent

.PHONY: redis
redis:
	-$(HELM) repo add bitnami https://charts.bitnami.com/bitnami
	-$(HELM) repo update
	$(HELM) upgrade --install redis bitnami/redis -n storm --create-namespace --values lightening-rod/redis/values.yaml


.PHONY: tetragon
tetragon: helm check-context
	-$(HELM) repo add cilium https://helm.cilium.io
	-$(HELM) repo update
	-$(HELM) upgrade --install tetragon cilium/tetragon -n honey --create-namespace --values honeystack/tetragon/values.yaml
	-kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=tetragon -n honey --timeout=5m 


.PHONY: vector
vector: helm 
	-$(HELM) repo add vector https://helm.vector.dev
	-$(HELM) upgrade --install vector vector/vector --namespace honey --create-namespace --values honeystack/vector/gkevalues.yaml
	-kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=vector  -n honey --timeout=5m 

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
	-$(MAKE) --makefile=Makefile_calibrate_kubehound calibration-traces

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
	-kubectl delete -f traces/9managed-identitytokenaccess.yaml
	-kubectl delete -f traces/10network-metadata.yaml
	-$(MAKE) --makefile=Makefile_calibrate_kubehound remove-calibration-traces

# Calling the other makefile
.PHONY: lightening
lightening:
	#-$(MAKE) --makefile=Makefile_calibrate_kubehound calibration-traces
	#-$(MAKE) --makefile=Makefile_calibrate_kubehound calibration-attack
	-kubectl apply -f attacks/lightening/deployment.yaml
	-kubectl apply -f attacks/lightening/cap-checker.yaml -n storm
	-kubectl create configmap check-script -n storm --from-file=attacks/lightening/check.sh

.PHONY: lightening-off
lightening-off:
	-kubectl delete configmap check-script -n storm
	-kubectl delete -f attacks/lightening/cap-checker.yaml -n storm
	-kubectl delete -f attacks/lightening/deployment.yaml
	#-$(MAKE) --makefile=Makefile_calibrate_kubehound remove-calibration-traces
	#-$(MAKE) --makefile=Makefile_calibrate_kubehound  remove-calibration-attack

.PHONY: sample-app
sample-app:
	$(MAKE) --makefile=cncf/harbor/Makefile install-helm install-harbor
	#-kubectl create ns pets
	#-kubectl apply -f https://raw.githubusercontent.com/Azure-Samples/aks-store-demo/main/aks-store-all-in-one.yaml -n pets
	

.PHONY: sample-app-off
sample-app-off:
	$(MAKE) --makefile=cncf/harbor/Makefile clean

## Experiments
## curretly candidate #1 for the network observability 
# the 1Gi limit is important on GKE else the scheduler gets confused, even if there s tons of RAM avail
.PHONY: pixie
pixie:
	px deploy --pem_memory_limit=1Gi 
	#-$(HELM) repo add pixie-operator https://artifacts.px.dev/helm_charts/operator 
	#-$(HELM) repo update
	#-$(HELM) upgrade --install  pixie pixie-operator/pixie-operator-chart --set cloudAddr=getcosmic.ai --set deployKey= --set clusterName=$(CLUSTER_NAME) --namespace pl --create-namespace 
	#helm repo add pixie-vizier https://artifacts.px.dev/helm_charts/vizier
	#helm repo update
	#helm install pixie pixie-vizier/vizier-chart --set deployKey= --set clusterName=$(CLUSTER_NAME) --namespace pl --create-namespace 

.PHONY: pixie-cli
pixie-cli:
	chmod +x ./honeystack/pixie/install.sh
	sudo bash -c "$(curl -fsSL https://getcosmic.ai/install.sh)"
	export PX_CLOUD_ADDR=getcosmic.ai
	px auth login
	px deploy -p=1Gi

.PHONY: pixie-airgap
pixie-airgap:
	git clone https://github.com/k8sstormcenter/pixie.git
	cd pixie/
	mkcert -install
	kubectl create ns plc
	./scripts/create_cloud_secrets.sh
	cd ../honeystack/pixie/pixie_cloud
	# remove job # actually dont, it gives an error
	kubectl apply -f yamls/cloud_deps_elastic_operator.yaml
	kubectl apply -f yamls/cloud_deps.yaml
	kubectl apply -f yamls/cloud.yaml


## kshark is useful if youre running in a high-stakes environment and you want pcaps
.PHONY: kshark
kshark:
	-$(HELM) repo add kubeshark https://helm.kubeshark.co
	-$(HELM) repo update
	-$(HELM) upgrade --install kubeshark kubeshark/kubeshark --create-namespace --namespace honey --values honeystack/kubeshark/values.yaml
	# kubectl port-forward service/kubeshark-front 8899:80


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
