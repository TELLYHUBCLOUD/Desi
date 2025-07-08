# Use official Python slim image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Install system-level dependencies (gcc, python3-dev, ffmpeg, aria2)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    ffmpeg \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for caching Docker layers)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy rest of your project files into container
COPY . .

# Expose port for Flask
EXPOSE 3000

# Final command to run your bot
CMD ["python", "Desi_video.py"]
