FROM paddlepaddle/paddle:2.6.2

WORKDIR /app

USER root

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Pre-download models for stable PaddleOCR 2.7.3
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', show_log=False, use_gpu=False)"

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
