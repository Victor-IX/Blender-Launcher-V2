# Dockerfile to build the project in a Debian environment
FROM python:3.10-slim-bullseye

WORKDIR /blv2

COPY . /blv2/

RUN apt-get update
RUN apt-get install -y \
    build-essential \
    linux-headers-amd64 \
    libglib2.0-0 libsm6 libxrender1 libxext6

RUN python3 -m pip install .
RUN python3 -m pip install xlib sip
RUN python3 build_style.py

ENTRYPOINT [ "bash" ]