FROM python:3.13-slim

# System deps kept minimal; all converters are pure-Python wheels.
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV HOST=0.0.0.0 \
    PORT=8000 \
    MAX_UPLOAD_MB=25

EXPOSE 8000

CMD ["python", "-m", "app"]
