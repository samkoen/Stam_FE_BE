FROM python:3.10-slim

# Install system dependencies required for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
# Note: We upgrade pip first to handle potential issues with older packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories for logs and storage if they don't exist
RUN mkdir -p logs user_storage

# Expose the port
EXPOSE 8000

# Set environment variables
ENV STAMSTAM_ENV=prod
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

