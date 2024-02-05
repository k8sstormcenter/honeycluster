NAME ?= honeypot
CLUSTER_NAME := $(NAME)

OS := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ARCH := $(shell uname -m | sed 's/x86_64/amd64/')

.EXPORT_ALL_VARIABLES:

##@ Kind

.PHONY: all-up
all-up: cluster-up tetragon-install ssh-install rbac sc-deploy  port-forward ## Create the kind cluster and deploy tetragon

.PHONY: detect-on
detect-on: traces

## Run this in a second shell to observe the STDOUT
.PHONY: secondshell-on
secondshell-on: 
	-kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon -c export-stdout -f |jq 'select(.process_kprobe != null) |  "\(.time) \(.process_kprobe.policy_name) \(.process_kprobe.function_name) \(.process_kprobe.process.binary) \(.process_kprobe.process.arguments) "'

.PHONY: attack
attack: copy-scripts create-bad exec

##@ Kind

.PHONY: cluster-up
cluster-up: kind ## Create the kind cluster
	-$(KIND) create cluster --name $(CLUSTER_NAME) --config config/kind-config.yaml 
	-cilium install --version 1.14.6
	kubectl -n kube-system wait --for=condition=Ready pod -l k8s-app=cilium

.PHONY: cluster-down
cluster-down: kind ## Delete the kind cluster
	-$(KIND) delete cluster --name $(CLUSTER_NAME)

##@ Tetragon

.PHONY: tetragon-install
tetragon-install: helm
	-$(HELM) repo add cilium https://helm.cilium.io
	-$(HELM) repo update
	-$(HELM) upgrade --install tetragon cilium/tetragon -n kube-system
	kubectl -n kube-system wait --for=condition=Ready pod  -l app.kubernetes.io/name=tetragon

.PHONY: traces
traces:
	#-kubectl apply -f traces/1sshd-probe-success.yaml
	-kubectl apply -f traces/2enumerate-serviceaccount.yaml
	#-kubectl apply -f traces/3enumerate-python.yaml
	-kubectl apply -f traces/4detect-scp-usage.yaml
	-kubectl apply -f traces/5detect-k8sapi-invoke.yaml
	#-kubectl apply -f traces/6detect-symlinkat.yaml
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
	-kubectl wait --for=condition=Ready pod -l app=bad-pv-pod
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
	-kubectl -n default wait --for=condition=Ready pod -l app.kubernetes.io/name=ssh-honeypot

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
	-kubectl exec bad-pv-pod  -- /bin/bash -c "cd /hostlogs/pods/default_bad-pv-**/bad-pv-pod/ && rm  0.log && ln -s /etc/kubernetes/pki/apiserver.key 0.log"


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