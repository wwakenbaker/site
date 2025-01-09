FROM python:latest

RUN apt-get update && apt-get install -y python3-dev && rm -rf /var/lib/apt/lists/*

COPY /server /server

RUN pip install -r /server/requirements.txt

WORKDIR /server

EXPOSE 5000

ENTRYPOINT ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

