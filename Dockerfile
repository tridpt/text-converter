FROM python:3.13-slim

# Install pandoc for high-fidelity conversions (LaTeX reading, tables/math).
RUN apt-get update \
    && apt-get install -y --no-install-recommends pandoc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV HOST=0.0.0.0 \
    PORT=8000 \
    MAX_UPLOAD_MB=25

EXPOSE 8000

CMD ["python", "-m", "app"]
