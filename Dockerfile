FROM python:3.11-slim

# Install ffmpeg and required libraries
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Elite Registry and worker script
COPY EliteRegistry.json .
COPY mashup.py .

# Sovereign zero-cloud worker container (all models executed via native DSP and EliteRegistry.json)

ENTRYPOINT ["python", "mashup.py", "--daemon"]
