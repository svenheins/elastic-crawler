FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY annotation_crawler.py .
RUN chmod +x annotation_crawler.py

CMD ["./annotation_crawler.py"]
