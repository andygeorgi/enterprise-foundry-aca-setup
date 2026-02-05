FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY sample_agent.py .

# Expose port for the agent UI
EXPOSE 8081

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the agent
CMD ["python", "sample_agent.py"]
