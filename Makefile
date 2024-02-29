NAME ?= honeypot
CLUSTER_NAME := $(NAME)

OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m | sed 's/x86_64/amd64/')
DIRS :=  extractcsv baseline signalminusbaseline
#DIRS :=    kprobe tracessshpre tracesssh  tracesenumpre tracesenum tracesscppre tracesscp tracesk8sclientpre tracesk8sclient tracessymlinkpre tracessymlink

.EXPORT_ALL_VARIABLES:

##@ Scenario

.PHONY: all-up
all-up: cluster-up tetragon-install redpanda jupyter vector ssh-install rbac sc-deploy port-forward ## Create the kind cluster and deploy tetragon

.PHONY: detect-on
detect-on: traces

## Run this in a second shell to observe the STDOUT
.PHONY: secondshell-on
secondshell-on: 
	-kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f | \
	jq 'select( .process_kprobe != null and .process_kprobe.process.pod.namespace == "default" ) | "\(.time) \(.process_kprobe.policy_name) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.process.pod.namespace) \(.process_kprobe.args[] | select(.sock_arg != null) | .sock_arg)"'


.PHONY: jquery-traces1
jquery-traces1:
	-kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f | \
	jq 'select( .process_kprobe != null and .process_kprobe.process.pod.namespace == "default" ) | "\(.time) \(.process_kprobe.policy_name) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.process.pod.namespace) \(.process_kprobe.args[] | select(.sock_arg.priority != null) | .sock_arg.priority)"'

.PHONY: attack
attack: copy-scripts create-bad exec

.PHONY: teardown
teardown: stop-port-forwarding sc-delete cluster-down

##@ Kind

.PHONY: cluster-up
cluster-up: kind ## Create the kind cluster
	-$(KIND) create cluster --name $(CLUSTER_NAME) --config config/kind-config.yaml

.PHONY: cluster-down
cluster-down: kind ## Delete the kind cluster
	-$(HELM) uninstall vector -n vector
	-$(HELM) uninstall redpanda-src -n redpanda
	-$(HELM) uninstall cert-manager -n cert-manager
	-$(HELM) uninstall tetragon -n kube-system
	-sleep 10
	-$(KIND) delete cluster --name $(CLUSTER_NAME)

.PHONY: stop-port-forwarding
stop-port-forwarding:
	-lsof -ti:5555 | xargs kill -9

.PHONY: sc-delete
sc-delete:
	kubectl delete po bad-pv-pod
	kubectl delete pvc bad-pv-claim-vol 
	kubectl delete pv bad-pv-volume-vol
	kubectl delete sc local-storage


.PHONY: redpanda
redpanda:
	-$(HELM) repo add jetstack https://charts.jetstack.io
	-$(HELM) repo update
	-$(HELM) upgrade --install cert-manager jetstack/cert-manager --set installCRDs=true --namespace cert-manager  --create-namespace
	-$(HELM) repo add redpanda https://charts.redpanda.com
	-$(HELM) repo update
	-$(HELM) upgrade --install redpanda-src redpanda/redpanda -n redpanda --create-namespace --values redpanda/values.yaml
	while [ "$$(kubectl -n redpanda get po -l app.kubernetes.io/name=redpanda -o jsonpath='{.items[0].metadata.generateName}')" != "redpanda-src-" ]; do \
		sleep 5; \
   	echo "Waiting for Redpanda pod to be created."; \
	done
	-kubectl -n redpanda wait --timeout=30s --for=condition=Ready pod -l app.kubernetes.io/component=redpanda-statefulset
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create cr1"

	
.PHONY: redpanda-wasm
redpanda-wasm:
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create tetragon" 
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create baseline && rpk topic alter-config baseline --set cleanup.policy=compact"
	@for dir in $(DIRS); do \
		cd redpanda/$$dir/ && go mod tidy && $(RPK) container start; $(RPK) transform build && cd ../.. ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create $$dir" ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "mkdir -p /tmp/$$dir" ;\
		kubectl cp redpanda/$$dir/transform.yaml redpanda/redpanda-src-0:/tmp/$$dir/. ;\
		kubectl cp redpanda/$$dir/$$dir.wasm redpanda/redpanda-src-0:/tmp/$$dir/. ;\
		kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "cd /tmp/$$dir/ && rpk transform deploy" ;\
	done

.PHONY: jupyter
spark:
	-$(HELM) repo add jupyterhub https://jupyterhub.github.io/helm-chart/
	-$(HELM) repo update
	-$(HELM) upgrade --install jupyterhub jupyterhub/jupyterhub --namespace jupyter --create-namespace  --values jupyterhub/values.yaml
	-echo "JHUB user/pass is yours to freely choose"


##@ Tetragon

.PHONY: tetragon-install
tetragon-install: helm
	-$(HELM) repo add cilium https://helm.cilium.io
	-$(HELM) repo update
	-$(HELM) upgrade --install tetragon cilium/tetragon -n kube-system --set tetragon.grpc.enabled=true --set tetragon.grpc.address=localhost:54321
	while [ "$$(kubectl -n kube-system get po -l app.kubernetes.io/name=tetragon -o jsonpath='{.items[0].metadata.generateName}')" != "tetragon-" ]; do \
		sleep 5; \
   	echo "Waiting for Tetragon pod to be created."; \
	done
	-kubectl -n kube-system wait --timeout=120s --for=condition=Ready pod -l app.kubernetes.io/name=tetragon


.PHONY: vector
vector:
	-$(HELM) repo add vector https://helm.vector.dev
	-$(HELM) upgrade --install vector vector/vector --namespace vector --create-namespace --values vector/values.yaml
	while [ "$$(kubectl -n vector get po -l app.kubernetes.io/name=vector -o jsonpath='{.items[0].metadata.generateName}')" != "vector-" ]; do \
		sleep 5; \
   	echo "Waiting for Vector pod to be created."; \
	done
	-kubectl -n vector wait --timeout=120s --for=condition=Ready pod -l app.kubernetes.io/name=vector

.PHONY: traces
traces:
	-kubectl apply -f traces/1sshd-probe-success.yaml
	-kubectl apply -f traces/2enumerate-serviceaccount.yaml
	-kubectl apply -f traces/3enumerate-python.yaml
	-kubectl apply -f traces/4detect-scp-usage.yaml
	-kubectl apply -f traces/5detect-k8sapi-invoke.yaml
	-kubectl apply -f traces/6detect-symlinkat.yaml
	-kubectl apply -f traces/7detect-sensitivefile-access.yaml

.PHONY: traces-off
traces-off:
	-kubectl delete -f traces/1sshd-probe-success.yaml
	-kubectl delete -f traces/2enumerate-serviceaccount.yaml
	-kubectl delete -f traces/3enumerate-python.yaml
	-kubectl delete -f traces/4detect-scp-usage.yaml
	-kubectl delete -f traces/5detect-k8sapi-invoke.yaml
	-kubectl delete -f traces/6detect-symlinkat.yaml
	-kubectl delete -f traces/7detect-sensitivefile-access.yaml

.PHONY: create-bad
create-bad:
	ssh -p 5555 -t root@127.0.0.1  'source priv-create.sh'
	-kubectl wait --for=condition=Ready pod my-pod
##@ vcluster setup

.PHONY: vcluster-deploy
vcluster-deploy: vcluster
	kubectl create namespace vcluster
	-$(VCLUSTER) create ssh -n vcluster --upgrade -f scenario/vc-values.yaml

.PHONY: kyverno-install
kyverno-install:
	-$(HELM) repo add kyverno https://kyverno.github.io/kyverno/
	-$(HELM) repo update
	-$(HELM) install kyverno kyverno/kyverno -n kyverno --create-namespace
	-$(HELM) install kyverno-policies kyverno/kyverno-policies -n kyverno --set podSecurityStandard=baseline --set validationFailureAction=enforce

.PHONY: ssh-install
ssh-install:
	-kubectl apply -f insecure-ssh/insecure-ssh.yaml
	-kubectl -n default wait --timeout=120s --for=condition=Ready pod -l app.kubernetes.io/name=ssh-honeypot

.PHONY: vcluster-disconnect
vcluster-disconnect: vcluster
	-$(VCLUSTER) disconnect

.PHONY: vcluster-connect
vcluster-connect: vcluster
	-$(VCLUSTER) connect ssh -n vcluster

.PHONY: rbac
rbac: 
	kubectl apply -f scenario/rbac.yaml

.PHONY: sc-deploy
sc-deploy:
	kubectl apply -f scenario/sc.yaml

.PHONY: port-forward
port-forward:
	kubectl port-forward svc/ssh-honeypot 5555:22 &

.PHONY: copy-scripts
copy-scripts:
	scp -P 5555 scripts/create.py scripts/priv-create.sh root@127.0.0.1:/root

.PHONY: ssh-connect
ssh-connect:
	ssh -p 5555 root@127.0.0.1

.PHONY: exec 
exec:
	-kubectl exec my-pod  -- /bin/bash -c "cd /hostlogs/pods/default_bad-pv-**/my-pod/ && rm  0.log && ln -s /etc/kubernetes/pki/apiserver.key 0.log"
	-kubectl logs my-pod


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

.PHONY: vcluster
VCLUSTER = $(shell pwd)/bin/vcluster
vcluster: ## Download vcluster if required
ifeq (,$(wildcard $(VCLUSTER)))
ifeq (,$(shell which vcluster 2> /dev/null))
	@{ \
		mkdir -p $(dir $(VCLUSTER)); \
		curl -L -o vcluster "https://github.com/loft-sh/vcluster/releases/latest/download/vcluster-$(OS)-$(ARCH)"; \
		sudo install -c -m 0755 vcluster $(shell pwd)/bin; \
		rm -f vcluster; \
	}
else
VCLUSTER = $(shell which vcluster)
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