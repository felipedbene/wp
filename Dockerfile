FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./
COPY *.sh ./

# Make scripts executable
RUN chmod +x *.sh

# Create a directory for credentials
RUN mkdir -p /app/credentials

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create entrypoint script
RUN echo '#!/bin/bash\n\
# Check if credentials are mounted\n\
if [ ! -f "/app/credentials/blog-credentials.json" ]; then\n\
    echo "Error: blog-credentials.json not found in /app/credentials/"\n\
    echo "Please mount your credentials as a Kubernetes secret"\n\
    exit 1\n\
fi\n\
\n\
# Copy credentials to working directory\n\
cp /app/credentials/blog-credentials.json /app/blog-credentials.json\n\
\n\
# Run the script\n\
python generate_and_publish_post.py\n\
' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
