# Use a base image with ssh and sshuttle installed
FROM ubuntu:20.04

# Avoid prompts during package installation
ARG DEBIAN_FRONTEND=noninteractive

# Install ssh, sshuttle and any other required packages
RUN apt-get update && apt-get install -y \
    openssh-server \
    sshuttle \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH daemon
RUN mkdir /var/run/sshd
RUN echo 'root:root' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# Expose SSH port
EXPOSE 22

# Start SSH daemon
CMD ["/usr/sbin/sshd", "-D"]

