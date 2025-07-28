FROM --platform=linux/amd64 python:3.10-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/output

ENTRYPOINT ["python", "main.py"]