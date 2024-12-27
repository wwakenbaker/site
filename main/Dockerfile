FROM python:latest

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY app.py /app/

COPY models.py /app/

EXPOSE 5000

ENTRYPOINT ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

WORKDIR /app