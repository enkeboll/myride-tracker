FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent data directory for SQLite database
VOLUME [ "/app/data" ]
ENV DB_URL="sqlite+aiosqlite:////app/data/myride.db"

CMD ["python", "main.py", "run"]
