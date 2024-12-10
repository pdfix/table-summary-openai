# Use the official Debian slim image as a base
FROM debian:bookworm-slim

# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/tab-sum-openai/

ENV VIRTUAL_ENV=venv


# Create a virtual environment and install dependencies
RUN python3 -m venv venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"


# Copy the source code and requirements.txt into the container
COPY src/ /usr/tab-sum-openai/src/
COPY requirements.txt /usr/tab-sum-openai/
COPY config.json /usr/tab-sum-openai/


RUN pip install --no-cache-dir -r requirements.txt 


ENTRYPOINT ["/usr/tab-sum-openai/venv/bin/python3", "/usr/tab-sum-openai/src/main.py"]
