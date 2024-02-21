NAME ?= honeypot
CLUSTER_NAME := $(NAME)

OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m | sed 's/x86_64/amd64/')
#DIRS := tracesscppre tracesscp
DIRS :=  tracessshpre tracesssh  tracesenumpre tracesenum tracesscppre tracesscp tracesk8sclientpre tracesk8sclient tracessymlinkpre tracessymlink
#DIRS := kprobe tracessshpre tracesssh tracesapipre tracesapi tracesenumpre tracesenum tracesscppre tracesscp tracesk8sclientpre tracesk8sclient tracessymlinkpre tracessymlink


KUBECONFIG := $(shell pwd)/.kubeconfig


.EXPORT_ALL_VARIABLES:

##@ put all on rke2
.PHONY: all-up
all-up: redpanda tetragon-install spyder vector spark


.PHONY: detect-on
detect-on: traces

## Run this in a second shell to observe the STDOUT
.PHONY: secondshell-on
secondshell-on: 
	-kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f |\
	jq 'select( .process_kprobe != null  \
	        and .process_kprobe.process.pod.namespace != "jupyter"   \
			and .process_kprobe.process.pod.namespace != "cert-manager" \
			and .process_kprobe.process.pod.namespace != "redpanda" \
			and .process_kprobe.process.pod.namespace != "spark" \
			and .process_kprobe.process.pod.namespace != "parseable" \
			and .process_kprobe.process.pod.namespace != "vector"  \
			and .process_kprobe.process.binary != "/usr/bin/rancher"  \
			and .process_kprobe.process.binary != "/usr/bin/webhook") | \
			"\(.)"'

# "\(.time) \(.process_kprobe.policy_name) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.process.pod.namespace) \(.process_kprobe.args[] | select(.sock_arg != null) | .sock_arg)"'


.PHONY: jquery-tracesscp
jquery-tracesscp:
	-kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f |\
	jq 'select( .process_kprobe.process.pod.namespace == "default" | .)'


.PHONY: jquery-traces1
jquery-traces1:
	-kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f |\
	jq 'select( .process_kprobe != null  \
	        and .process_kprobe.process.pod.namespace != "jupyter"   \
			and .process_kprobe.process.pod.namespace != "cert-manager" \
			and .process_kprobe.process.pod.namespace != "redpanda" \
			and .process_kprobe.process.pod.namespace != "spark" \
			and .process_kprobe.process.pod.namespace != "parseable" \
			and .process_kprobe.process.binary == "/usr/sbin/sshd" \
			and .process_kprobe.process.pod.namespace != "vector" )| \
	 "\(.time) \(.process_kprobe.policy_name) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) \(.process_kprobe.process.pod.namespace) \(.process_kprobe.args[] )"'


.PHONY: attack
attack: copy-scripts create-bad exec

##@ Kind



.PHONY: redpanda
redpanda:
	-$(HELM) repo add redpanda https://charts.redpanda.com
	-$(HELM) repo update
	-$(HELM) upgrade --install redpanda-src redpanda/redpanda -n redpanda --create-namespace --values redpanda/rke2values.yaml
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create cr1"

# Its about time to make this into a loop


.PHONY: redpanda-wasm
redpanda-wasm:
	-kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create tetragon" 
	@for dir in $(DIRS); do \
		cd redpanda/$$dir/ && go mod tidy && rpk transform build && cd ../.. ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "rpk topic create $$dir" ;\
		kubectl exec -it -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "mkdir -p /tmp/$$dir" ;\
		kubectl cp redpanda/$$dir/transform.yaml redpanda/redpanda-src-0:/tmp/$$dir/. ;\
		kubectl cp redpanda/$$dir/$$dir.wasm redpanda/redpanda-src-0:/tmp/$$dir/. ;\
		kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "cd /tmp/$$dir/ && rpk transform deploy" ;\
	done

.PHONY: jupyter
jupyter:
	-$(HELM) repo add jupyterhub https://jupyterhub.github.io/helm-chart/
	-$(HELM) repo update
	-$(HELM) upgrade --install jupyterhub jupyterhub/jupyterhub --namespace jupyter --create-namespace  --values jupyterhub/rke2values.yaml



##@ Tetragon

.PHONY: tetragon-install
tetragon-install: helm
	-$(HELM) repo add cilium https://helm.cilium.io
	-$(HELM) repo update
	-$(HELM) upgrade --install tetragon cilium/tetragon -n kube-system --set tetragon.grpc.enabled=true --set tetragon.grpc.address=localhost:54321
	kubectl -n kube-system wait --for=condition=Ready pod  -l app.kubernetes.io/name=tetragon


.PHONY: vector
vector:
	-$(HELM) repo add vector https://helm.vector.dev
	-$(HELM) upgrade --install vector vector/vector --namespace vector --create-namespace --values vector/values.yaml


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

.PHONY: create-bad
create-bad:
	ssh -p 8888 -t root@137.117.185.70  'source priv-create.sh'
	-kubectl wait --for=condition=Ready pod -l app=my-pod
##@ vcluster setup


.PHONY: ssh-install
ssh-install:
	-kubectl apply -f insecure-ssh/rke2insecure-ssh.yaml
	-kubectl -n default wait --for=condition=Ready pod -l app.kubernetes.io/name=ssh-proxy

.PHONY: rbac
rbac: 
	kubectl apply -f scenario/rbac.yaml

.PHONY: sc-deploy
sc-deploy:
	kubectl apply -f scenario/sc.yaml

.PHONY: port-forward
port-forward:
	-kubectl cp id_rsa  default/ssh-proxy:/.
	-kubectl exec -i -t ssh-proxy -- /bin/bash -c " ssh -R8888:localhost:22 paris@137.117.185.70 -i id_rsa &"

.PHONY: copy-scripts
copy-scripts:
	scp -P 8888 scripts/create.py scripts/priv-create.sh root@137.117.185.70:/root

.PHONY: ssh-connect
ssh-connect:
	ssh root@137.117.185.70 -p 8888

.PHONY: exec 
exec:
	-kubectl exec my-pod  -- /bin/bash -c "cd /hostlogs/pods/default_my-**/my-pod/ && rm  0.log && ln -s /etc/kubernetes/pki/apiserver.key 0.log"


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