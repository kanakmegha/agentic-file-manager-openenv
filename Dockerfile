FROM python:3.11-slim

WORKDIR /app

# 1. Update system packages (Good for stability)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Install dependencies first (Layer Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the project
COPY . .

# 4. Standard Port
EXPOSE 8000

# 5. Start command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]