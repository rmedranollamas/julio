FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create skills directory
RUN mkdir -p /skills

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the agent
CMD ["python", "main.py"]
