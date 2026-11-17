# Toolchain for preprocessing: the SySeVR authors' released code (github.com/SySeVR/SySeVR, pinned
# commit) on Ubuntu 20.04, with Joern 0.3.1, Neo4j 2.1.5 (Java) and Python 2.7 for the paper's scripts.
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-8-jdk-headless ant git ca-certificates curl bzip2 time procps python3 lsof \
    && rm -rf /var/lib/apt/lists/*

# Python 2.7 through micromamba and conda-forge. python-igraph 0.7.1 for Python 2.7 needs icu 58.
ENV MAMBA_ROOT_PREFIX=/opt/mamba
RUN curl -fsSL -o /usr/local/bin/micromamba https://github.com/mamba-org/micromamba-releases/releases/download/1.5.8-0/micromamba-linux-64 \
    && chmod +x /usr/local/bin/micromamba \
    && micromamba create -y -p /opt/py27 -c conda-forge python=2.7 python-igraph icu=58 pip \
    && micromamba clean -a -y
ENV PY27=/opt/py27/bin/python

# Only the parts of the SySeVR repository we need, at a fixed commit.
ARG SYSEVR_COMMIT=db9ceaf351185b281c45bfb95f221b5fe741f928
RUN git clone -q --filter=blob:none --no-checkout https://github.com/SySeVR/SySeVR /opt/sysevr \
    && cd /opt/sysevr && git sparse-checkout init --cone \
    && git sparse-checkout set Implementation SySeVR_docker/docker_build/home/SySeVR/joern-0.3.1 \
           SySeVR_docker/docker_build/home/SySeVR/neo4j \
           SySeVR_docker/docker_build/home/SySeVR/softdir/py2neo-py2neo-2.0 \
           SySeVR_docker/docker_build/home/SySeVR/softdir/python-joern-0.3.1 \
    && git checkout -q $SYSEVR_COMMIT \
    && mv SySeVR_docker/docker_build/home/SySeVR/joern-0.3.1 /opt/joern \
    && mv SySeVR_docker/docker_build/home/SySeVR/neo4j /opt/neo4j \
    && mv SySeVR_docker/docker_build/home/SySeVR/softdir /opt/softdir && rm -rf SySeVR_docker .git

# Python 2.7 libraries for the slicer. py2neo 2.0 and python-joern come from the SySeVR repository itself.
RUN /opt/py27/bin/pip install -q /opt/softdir/py2neo-py2neo-2.0 \
    && /opt/py27/bin/pip install -q git+https://github.com/fabsx00/py2neo-gremlin.git@c94d29038802d67f49e0fee56c9344384d1f0fdb \
    && /opt/py27/bin/pip install -q --no-deps /opt/softdir/python-joern-0.3.1 \
    && /opt/py27/bin/pip install -q xlrd==1.2.0

# Build Joern 0.3.1.
RUN cd /opt/joern && ant -q && test -f bin/joern.jar && chmod +x /opt/neo4j/bin/*

# gensim 3.4 for word2vec, the version the SySeVR README names. smart_open 1.8.4 is the last release that still
# imports on Python 2.7.
RUN micromamba install -y -p /opt/py27 -c conda-forge gensim=3.4.0 && micromamba clean -a -y \
    && /opt/py27/bin/pip install -q smart_open==1.8.4 \
    && /opt/py27/bin/python -c "import gensim; assert gensim.__version__ == '3.4.0'"

COPY . /preprocessing
RUN chmod +x /preprocessing/*.sh /preprocessing/steps/*.sh /preprocessing/scripts/*.sh
WORKDIR /work
ENTRYPOINT ["/preprocessing/run.sh"]
