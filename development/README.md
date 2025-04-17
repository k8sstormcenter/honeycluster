# Development Tools

This folder contains resources used **only for local development, testing, and training**.  
⚠️ Do not deploy these tools in production or research clusters.

---

## 📦 Tools

### 1. `redis-insight.yaml`
A simple deployment of Redis Insight — a UI for inspecting Redis state.  
Used for debugging, viewing temporary keys, and development.

---

### 2. `pem-custom.yaml`  
A **custom Pixie Edge Module (PEM)** deployment, running as a DaemonSet on your local cluster.

This PEM is:
- Built from our [forked Pixie repo](https://github.com/k8sstormcenter/pixie)
- Modified to support custom data sources (e.g., Tetragon logs)
- Packaged into a local Docker image (`custom-pem:dev`)
- Deployed to the cluster manually via Makefile

---

## 💠 Pixie Local Development

### ⚖️ Dependencies

To build and run the full Pixie stack locally, you need:

- [Bazelisk](https://github.com/bazelbuild/bazelisk) (auto-manages correct Bazel version)
- Docker (for image packaging)
- A Kubernetes cluster (we use [k0s](https://docs.k0sproject.io/) locally)

---

### ♻️ Installing Bazelisk on Ubuntu

```bash
# Install Bazelisk (no need to remove existing Bazel)
curl -Lo bazelisk https://github.com/bazelbuild/bazelisk/releases/download/v1.20.0/bazelisk-linux-amd64
chmod +x bazelisk
sudo mv bazelisk /usr/local/bin/bazel
```

To verify it works:

```bash
cd ../pixie   # or wherever you cloned the Pixie repo
bazel version
```

It should download and use Bazel **6.2.0** (as defined in the repo's `.bazelversion`).

---
Also, make sure your local env is ready for python3-dev

```bash
sudo apt install python3-dev -y
```

---

### ⚙️ Building the Full Pixie Stack

You can now build **all Pixie components** and package them into a local Docker image.
Run this from your `honeycluster` folder:

```bash
make dev-pixie
```

This will:
1. Use Bazel to build the full Pixie system (not just PEM)
2. Build a Docker image tagged `custom-pixie:dev`
3. Deploy it to your local `honey` namespace

---

### 🐫 Local Image Notes

We do **not push** the image to a remote registry. Instead:

- The image is built locally
- `imagePullPolicy: Never` ensures Kubernetes uses the local copy
- Works great for local single-node setups (like k0s)

---

### 🚀 Deploying the Pixie Stack

If needed separately:

```bash
docker build -t custom-pixie:dev -f pixie/Dockerfile .
kubectl apply -f development/pem-custom.yaml
```

Then check:

```bash
kubectl get pods -n honey -l app=custom-pem
kubectl logs -n honey -l app=custom-pem
```

---

### What we're testing

This setup helps us explore:
- Ingesting Tetragon and Kubescape logs at node level
- Feeding that data into Pixie’s pipeline
- Creating custom Pixie tables
- Exporting or visualizing in STIX format later

---

### 🛠️ Future Improvements

- Build and package Vizier UI locally
- Explore alternative visualizations
- Automate Pixie cluster setup + custom sources

---

> Questions or updates? Ping Berk or Constanze.

