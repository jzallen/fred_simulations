FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up a non-root user
RUN useradd -m fred
USER fred
WORKDIR /home/fred

# Clone FRED public repository
RUN git clone https://github.com/PublicHealthDynamicsLab/FRED.git fred-framework

ENV PATH="/home/fred/fred-framework/bin:${PATH}"
