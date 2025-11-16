FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install Python and pip
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends python3 python3-pip python3-venv python3-requests \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management (optional)
RUN pip3 install --break-system-packages --no-cache-dir uv || true
