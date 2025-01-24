#!/bin/bash

python init_db.py

exec gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --log-level=error