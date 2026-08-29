FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# levels, tickets and warnings live here - mount it so they survive restarts
VOLUME ["/app/data"]

CMD ["python", "-u", "bot.py"]
