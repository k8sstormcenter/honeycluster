FROM ubuntu:22.04

# Install necessary tools
RUN apt-get update && \
    apt-get install -y \
    kmod \
    iptables \
    mitmproxy \
    iproute2 \
    net-tools \
    strace \
    netcat \
    curl\
    jq\
    libcap2-bin \
    && apt-get clean
# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/


# Set up the entrypoint
ENTRYPOINT ["/bin/bash"]