import time

from flask import Flask, jsonify, request, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Tweets, Users

# Create a flask app
app = Flask(__name__)

# Create a SQLAlchemy engine
engine = create_engine(
    'postgresql+psycopg2://postgres:postgres@postgres_container:5432/postgres', echo=True
)

# Create SQLAlchemy session
session = Session(bind=engine)

@app.before_request
def create_tables():
    with session:
        Base.metadata.drop_all(bind=engine) # Drop all tables
        Base.metadata.create_all(bind=engine) # Create tables if they don't exist
        session.add(Users(user_id=1, api_key='123321'))
        session.commit()

@app.route('/')
def main():
    return render_template("index.html")

@app.route('/api/tweets', methods=['POST'])
def create_tweet():
    # Get tweet data from request
    _api_key = request.form.get('api_key')
    content = request.form.get('content')

    with session:
        if session.query(Users).filter(Users.api_key == _api_key).first():

        # Create a new tweet object
            _author = session.query(Users.user_id).where(Users.api_key == _api_key).first()[0]
            tweet = Tweets(
                author=_author,
                content=content,
            )

        else:
            return jsonify(error='Invalid API key'), 401

    # Add the tweet to the database
    with session:
        session.add(tweet)
        session.commit()

    return jsonify(tweet_id=tweet.tweet_id), 201


