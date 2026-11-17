# The PyTorch version of SySeVR's BGRU, CPU only, on Ubuntu 20.04 and its Python 3.8.
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
# torch 2.4.1 is the last release that supports Python 3.8. We install the CPU-only build.
RUN pip3 install --no-cache-dir numpy==1.24.4 \
    && pip3 install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu
COPY *.py /model/
WORKDIR /model
ENTRYPOINT ["python3"]
