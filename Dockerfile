FROM python:3-alpine3.20

WORKDIR /app

COPY . /app

RUN chmod 644 /app

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python","./app.py"]