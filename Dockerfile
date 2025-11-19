# ---- Base Stage ----
# Use an official Python runtime as a parent image
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# --- Install system dependencies in steps for robustness ---

# Step 1: Update and install base build tools + ffmpeg
RUN apt-get update && \
    apt-get install -y curl ca-certificates gnupg build-essential ffmpeg --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Step 2: Add NodeSource repository for Node.js with proper key setup
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list

# Step 3: Install Node.js
RUN apt-get update && \
    apt-get install -y nodejs --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# ---- Builder Stage ----
FROM base AS builder

# Install build dependencies
RUN pip install --upgrade pip

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ---- Final Stage ----
FROM base AS final

# Copy the pre-built wheels from the builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*
COPY . .
# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "main.py"]