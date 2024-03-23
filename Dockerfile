FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y postgresql-client

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--reload"]