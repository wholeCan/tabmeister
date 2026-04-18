FROM python:3.12-slim

WORKDIR /app

COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/app.py .
COPY web/templates/ templates/

CMD ["python", "app.py"]
