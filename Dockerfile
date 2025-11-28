FROM python:3.12-slim

# Install system deps required by opencv and runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libgl1-mesa-glx \
       libglib2.0-0 \
       libsm6 \
       libxrender1 \
       libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy and install Python deps
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . /app

# Use a non-root user for better security
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

ENV PORT=5000
EXPOSE 5000

# Use gunicorn for production
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
