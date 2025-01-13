from typing import Dict

from sqlalchemy import create_engine, ColumnElement
from sqlalchemy.orm import Session

from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from models import Base, Tweets, Users, Follows
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

def like(tweet: Tweets, user_id: ColumnElement[int]) -> Dict:
    _list = list(tweet.users_who_liked)
    _list.append(user_id)
    tweet.users_who_liked = _list
    tweet.likes += 1
    session.commit()
    return {"result": True}

def unlike(tweet: Tweets, user_id: ColumnElement[int]) -> Dict:
    _list = list(tweet.users_who_liked)
    _list.remove(user_id)
    tweet.users_who_liked = _list
    tweet.likes -= 1
    session.commit()
    return {"result": True}

def check_api_key(api_key):
    # Check if the API key is valid
    return session.query(Users).filter(
        Users.api_key == api_key).first() is not None

def check_belonging_tweet(tweet_id, api_key):
    # Check if the tweet belongs to the specified user
    author_id = session.query(Users.user_id).where(
        Users.api_key == api_key).first()[0]
    return session.query(Tweets).filter(
        Tweets.tweet_id == tweet_id,
        Tweets.author_id == author_id).first() is not None

@app.post('/api/tweets/{api_key: str}')
def create_tweet(data: CreateTweetSchema, api_key):
    # Get tweet data from request
    _api_key = api_key
    tweet_data = data.tweet_data
    #tweet_media_ids = data.tweet_media_ids

    with session:
        if check_api_key(_api_key):

        # Create a new tweet object
            _author_id = session.query(Users.user_id).where(
                Users.api_key == _api_key).first()[0]
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
            return HTTPException(status_code=401,
                                 detail="Invalid API key")

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
                                     detail="Tweet not found or "
                                            "not belonging to the user")
        else:
            return HTTPException(status_code=401,
                                 detail="Invalid API key")

@app.post('/api/tweets/{tweet_id: int}/likes/{api_key: str}')
def like_tweet(tweet_id: int, api_key: str):
    with session:
        if check_api_key(api_key):
            tweet = session.query(Tweets).get(tweet_id)
            if tweet:
                user_id = session.query(Users.user_id).where(
                    Users.api_key == api_key).first()[0]
                if not user_id in tweet.users_who_liked:
                    return like(tweet, user_id)
                else:
                    return HTTPException(status_code=409,
                                         detail="User already liked the tweet")
            else:
                return HTTPException(status_code=404,
                                         detail="Tweet not found")
        else:
            return HTTPException(status_code=401,
                                 detail="Invalid API key")

@app.delete('/api/tweets/{tweet_id: int}/likes/{api_key: str}')
def unlike_tweet(tweet_id: int, api_key: str):
    with session:
        if check_api_key(api_key):
            tweet = session.query(Tweets).get(tweet_id)
            if tweet:
                user_id = session.query(Users.user_id).where(
                    Users.api_key == api_key).first()[0]
                if user_id in tweet.users_who_liked:
                    return unlike(tweet, user_id)
                else:
                    return HTTPException(status_code=409,
                                         detail="User is not currently liking the tweet")
            else:
                return HTTPException(status_code=404,
                                         detail="Tweet not found")
        else:
            return HTTPException(status_code=401,
                                 detail="Invalid API key")


@app.post('/api/users/{id_user: int}/follow/{api_key: str}')
def follow_user(id_user: int, api_key: str):
    # Handle user following logic here
    with session:
        if check_api_key(api_key):
            follower_id = session.query(Users.user_id).where(
                Users.api_key == api_key).first()[0]
            following_id = id_user

            if follower_id == following_id:
                return HTTPException(status_code=400,
                                         detail="Cannot follow yourself")

            if not session.query(Follows).filter(
                    Follows.follower == follower_id,
                    Follows.following == following_id).first():
                session.add(Follows(follower=follower_id, following=following_id))
                session.commit()
                return {"result": True}
            else:
                return HTTPException(status_code=409,
                                     detail="User is already following the specified user")
        else:
            return HTTPException(status_code=401,
                                 detail="Invalid API key")

@app.delete('/api/users/{id_user: int}/follow/{api_key: str}')
def unfollow_user(id_user: int, api_key: str):
    with session:
        if check_api_key(api_key):
            follower_id = session.query(Users.user_id).where(
                Users.api_key == api_key).first()[0]
            following_id = id_user

            follow = session.query(Follows).filter(
                Follows.follower == follower_id,
                Follows.following == following_id).first()

            if follow:
                session.delete(follow)
                session.commit()
                return {"result": True}
            else:
                return HTTPException(status_code=404,
                                     detail="User is not following the specified user")
        else:
            return HTTPException(status_code=401,
                                 detail="Invalid API key")

@app.get('/api/tweets/{api_key: str}')
def get_tweets(api_key: str):
    # Get all tweets for the specified user
    with session:
        if check_api_key(api_key):
            author_id = session.query(Users.user_id).where(
                Users.api_key == api_key).first()[0]
            tweets = session.query(Tweets).filter(Tweets.author_id != author_id)
            return {"result": True}, {"tweets":
                                          [{"id": tweet.tweet_id,
                                          "content": tweet.tweet_data,
                                          "author": tweet.author_id,
                                          "likes": tweet.likes,
                                          "users_who_liked":
                                                [user for user in tweet.users_who_liked]}
                                                for tweet in tweets]}

        else:
            return HTTPException(status_code=401,
                                 detail="Invalid API key")


app.mount("/static", StaticFiles(directory="../client/static"), name="static")
app.mount("/js", StaticFiles(directory="../client/static/js"), name="js")
app.mount("/css", StaticFiles(directory="../client/static/css"), name="css")

create_tables()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000)
