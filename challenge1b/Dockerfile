FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache

COPY . .

ENTRYPOINT ["python", "main.py"] 