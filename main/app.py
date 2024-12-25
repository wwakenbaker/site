from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Create a flask app
app = Flask(__name__)

# Create a SQLAlchemy engine
engine = create_engine('postgresql+psycopg2://postgres:postgres@postgres_container:5432/db', echo=True)

# Create SQLAlchemy session
session = Session(bind=engine)


