# ---- Base Stage ----
# Use an official Python runtime as a parent image
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

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

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "main.py"]