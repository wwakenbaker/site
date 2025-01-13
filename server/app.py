from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from models import Base, Tweets, Users
from schemas import CreateTweetSchema

# Create a fastapi app
app = FastAPI()

# Create a SQLAlchemy engine
engine = create_engine(
    'postgresql+psycopg2://postgres:postgres@localhost:5432/postgres', echo=True
)

# Create SQLAlchemy session
session = Session(bind=engine)

def create_tables():
    with session:
        Base.metadata.drop_all(bind=engine) # Drop all tables
        Base.metadata.create_all(bind=engine) # Create tables if they don't exist
        session.add(Users(user_id=1, api_key='test_api_key_1'))
        session.commit()

@app.get('/')
def main():
    return FileResponse("../client/static/index.html")

def check_api_key(api_key):
    # Check if the API key is valid
    return session.query(Users).filter(Users.api_key == api_key).first() is not None

def check_belonging_tweet(tweet_id, api_key):
    # Check if the tweet belongs to the specified user
    author_id = session.query(Users.user_id).where(Users.api_key == api_key).first()[0]
    return session.query(Tweets).filter(
        Tweets.tweet_id == tweet_id, Tweets.author_id == author_id).first() is not None

@app.post('/api/tweets/{api_key: str}')
def create_tweet(data: CreateTweetSchema, api_key):
    # Get tweet data from request
    _api_key = api_key
    tweet_data = data.tweet_data
    #tweet_media_ids = data.tweet_media_ids

    with session:
        if check_api_key(_api_key):

        # Create a new tweet object
            _author_id = session.query(Users.user_id).where(Users.api_key == _api_key).first()[0]
            tweet = Tweets(
                author_id=_author_id,
                tweet_data=tweet_data,
                #tweet_media_ids=tweet_media_ids,
            )
            # Add the tweet to the database
            session.add(tweet)
            session.commit()
            tweet_id = tweet.tweet_id
        else:
            return HTTPException(status_code=401, detail="Invalid API key")

    return {"result": True, "tweet_id": tweet_id}

@app.post('/api/medias/{api_key: str}')
def upload_media(api_key):
    # Handle media upload logic here
    pass

@app.delete('/api/tweets/{tweet_id: int}/{api_key: str}')
def delete_tweet(tweet_id: int, api_key: str):
    with session:
        if check_api_key(api_key):
            tweet = session.query(Tweets).get(tweet_id)
            if check_belonging_tweet(tweet_id, api_key):
                session.delete(tweet)
                session.commit()
                return {"result": True}
            else:
                return HTTPException(status_code=404,
                                     detail="Tweet not found or not belonging to the user")
        else:
            return HTTPException(status_code=401, detail="Invalid API key")


app.mount("/static", StaticFiles(directory="../client/static"), name="static")
app.mount("/js", StaticFiles(directory="../client/static/js"), name="js")
app.mount("/css", StaticFiles(directory="../client/static/css"), name="css")

create_tables()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000)
