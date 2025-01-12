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

@app.post('/api/tweets')
def create_tweet(data: CreateTweetSchema):
    # Get tweet data from request
    _api_key = data.author_key
    content = data.content

    with session:
        if session.query(Users).filter(Users.api_key == _api_key).first():

        # Create a new tweet object
            _author_id = session.query(Users.user_id).where(Users.api_key == _api_key).first()[0]
            tweet = Tweets(
                author_id=_author_id,
                content=content,
            )
            # Add the tweet to the database
            session.add(tweet)
            tweet_id = tweet.tweet_id
            session.commit()
        else:
            return HTTPException(status_code=401, detail="Invalid API key")

    return {"result": True, "tweet_id": tweet_id}

app.mount("/static", StaticFiles(directory="../client/static"), name="static")
app.mount("/js", StaticFiles(directory="../client/static/js"), name="js")
app.mount("/css", StaticFiles(directory="../client/static/css"), name="css")

create_tables()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000)
