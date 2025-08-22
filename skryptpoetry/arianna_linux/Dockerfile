FROM python:3.11-slim

# Install build tools, Julia runtime, and OpenJDK for CPU-only usage
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        julia \
        openjdk-17-jdk && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["python", "bridge.py"]
