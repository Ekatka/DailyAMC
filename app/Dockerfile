FROM python:3.10


WORKDIR /app

RUN apt-get update && apt-get install -y git curl libmcrypt-dev default-mysql-client

COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

COPY . /app
RUN  chmod +x wait-for-mysql.sh
EXPOSE 8000
#CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]