FROM python:3.11-slim

WORKDIR /app

# ── system deps for Node (React build) ───────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Python deps ───────────────────────────────────────────────────
# Install CPU-only PyTorch first to avoid the ~2GB CUDA variant
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model during build to avoid cold-start delay
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# ── copy source ───────────────────────────────────────────────────
COPY . .

# ── build React app ───────────────────────────────────────────────
RUN cd react-app && npm install --legacy-peer-deps && npm run build

EXPOSE 8000

# ── start.py handles ingest-on-first-boot then launches server ────
CMD ["python", "start.py"]
