FROM ubuntu:latest

# Install necessary tools
RUN apt-get update && \
    apt-get install -y \
    kmod \
    iptables \
    mitmproxy \
    iproute2 \
    net-tools \
    && apt-get clean

# Set up the entrypoint
ENTRYPOINT ["/bin/bash"]