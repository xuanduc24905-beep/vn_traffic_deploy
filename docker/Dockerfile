FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_PATH=/app/models/best.onnx \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

WORKDIR /app

# Cài thư viện trước để tận dụng cache layer khi chỉ sửa code
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY gunicorn.conf.py .
COPY app/ app/
COPY models/best.onnx models/

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["gunicorn", "app.main:app"]
