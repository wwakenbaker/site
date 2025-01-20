FROM python:latest

RUN apt-get update && apt-get install -y python3-dev && rm -rf /var/lib/apt/lists/*

COPY /server /server

WORKDIR /server

RUN pip install -U pip setuptools

RUN pip install "cython<3.0.0" wheel && pip install "pyyaml==5.4.1" --no-build-isolation

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["./start.sh"]
