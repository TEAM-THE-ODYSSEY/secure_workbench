FROM python:3.12-slim

# System dependencies for PDF processing and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \

    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Lightweight CPU PyTorch first
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies with CPU index fallback
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu



# Download spaCy model
RUN python -m spacy download en_core_web_sm || true

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Default: run FastAPI server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
