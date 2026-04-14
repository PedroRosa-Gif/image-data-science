FROM python:3.11-slim-bullseye

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libatlas-base-dev \
    libfftw3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/LIDS-UNICAMP/ift /app/ift
WORKDIR /app/ift
RUN make

ENV NEWIFT_DIR=/app/ift
ENV LD_LIBRARY_PATH=/app/libift/lib

WORKDIR /app/reslicing
COPY . .

RUN make reslicing
RUN make MIP

RUN ls -l /app/reslicing

RUN pip install --no-cache-dir streamlit numpy opencv-python

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]