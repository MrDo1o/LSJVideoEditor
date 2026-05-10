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

# We assume the host mounts the Topaz Video AI bundle to /Applications/Elite Video AI.app
# so the script can access the proprietary binaries.
# e.g. docker run -v "/Applications/Topaz Video AI.app":"/Applications/Elite Video AI.app" elite-worker

ENTRYPOINT ["python", "mashup.py", "--daemon"]
