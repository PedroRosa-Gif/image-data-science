FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Dependências para compilar o IFT
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libatlas-base-dev \
    libfftw3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clona e compila o IFT
RUN git clone https://github.com/LIDS-UNICAMP/ift.git
WORKDIR /app/ift
RUN make

# Volta pro projeto
WORKDIR /app

# Copia seu código
COPY . .

# Compila seu DIFT
WORKDIR /app/volumetric-segmentation
RUN make DIFT

# Diretório de trabalho onde os dados serão montados
WORKDIR /data

# Executa o DIFT
ENTRYPOINT ["/app/volumetric-segmentation/DIFT"]