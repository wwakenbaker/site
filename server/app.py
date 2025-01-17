from typing import Dict

import asyncio
import starlette
from fastapi import FastAPI, HTTPException, UploadFile, Form, Depends
from fastapi.params import File, Query
from sqlalchemy import ColumnElement
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles

from models import Base, Tweets, Users, Follows, Medias
from schemas import CreateTweetSchema, FileUploadResponse

# Create a fastapi app
app = FastAPI()

# Create a SQLAlchemy engine
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
engine = create_async_engine(DATABASE_URL, echo=True)

# Create SQLAlchemy session
async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        async with session.begin():
            session.add(Users(user_id=1, api_key='test_api_key_1'))
            session.add(Users(user_id=2, api_key='test_api_key_2'))
        await session.commit()

async def check_api_key(api_key) -> bool:
    # Check if the API key is valid
    async with async_session() as session:
        return await session.execute(
            select(Users.user_id).where(Users.api_key == api_key)
        ) is not None

async def check_belonging_tweet(tweet_id, api_key) -> bool:
    async with async_session() as session:
        if check_api_key(api_key):
            # Check if the tweet belongs to the specified user
            author_id = await session.execute(
                select(Tweets.author_id).where(
                    Tweets.tweet_id == tweet_id)
            )
            author_id = author_id.scalars().first()
            return await session.execute(
                select(Tweets).filter(
                    Tweets.tweet_id == tweet_id,
                    Tweets.author_id == author_id)
                ) is not None

async def like(tweet: Tweets, user_id: ColumnElement[int]) -> Dict:
    async with async_session() as session:
        _list = list(tweet.users_who_liked)
        _list.append(user_id)
        tweet.users_who_liked = _list
        tweet.likes += 1
        await session.commit()
        return {"result": True}

async def unlike(tweet: Tweets, user_id: ColumnElement[int]) -> Dict:
    async with async_session() as session:
        _list = list(tweet.users_who_liked)
        _list.remove(user_id)
        tweet.users_who_liked = _list
        tweet.likes -= 1
        session.commit()
        return {"result": True}

async def validate_str(tweet_data: str = Form(...)):
       return tweet_data

@app.get('/', tags=["MAIN"])
async def main():
    return FileResponse("../client/static/index.html")

@app.get('/api/tweets/', tags=["TWEETS"])
async def get_tweets(api_key: str):
    # Get all tweets for the specified user
    async with async_session() as session:
        if check_api_key(api_key):
            author_id = await session.execute(
                select(Users.user_id).where(Users.api_key == api_key)
            )
            author_id = author_id.scalars().first()
            tweets = await session.execute(
                select(Tweets).filter(Tweets.author_id != author_id)
            )
            tweets = tweets.scalars().all()
            try:
                return {"result": True, "tweets":
                    [{"id": tweet.tweet_id,
                    "content": tweet.tweet_data,
                    "attachments": [
                                   f"/api/medias/{i_attachment}"
                                   for i_attachment in tweet.attachments_ids
                                   ],
                    "author": {"id": tweet.author_id},
                    "likes": [{"user_id": user_id} for user_id in tweet.users_who_liked]}
                        for tweet in tweets]}
            except Exception as e:
                return {
                    "result": False,
                    "error_type": str(type(e).__name__),
                    "error_message": str(e)
                }

        else:
            raise HTTPException(status_code=401,
                                 detail="Invalid API key")

async def get_media_path(media_id: int):
    with async_session() as session:
        media = await session.execute(
            select(Medias).filter(Medias.media_id == media_id)
        )
        return Response(content=media.file_body, media_type="image/png")

@app.post('/api/tweets/', tags=["TWEETS"])
async def create_tweet(tweet_data: CreateTweetSchema = Depends(validate_str),
                 api_key: str = Query(...),
                 attachments: UploadFile = File(...)):
    async with async_session() as session:
        async with session.begin():
            # Check if the API key is valid
            if check_api_key(api_key):
                #Check media files if provided and upload them
                if isinstance(attachments, starlette.datastructures.UploadFile):
                    attachments_ids = await upload_media(attachments)
                elif isinstance(attachments, list):
                    attachments_ids = [await upload_media(file) for file in attachments]
            # Get the author ID based on the API key
                result = await session.execute(
                    select(Users.user_id).where(Users.api_key == api_key)
                )
                _author_id = result.scalars().first()
            # Create a new tweet object
                tweet = Tweets(
                    author_id=_author_id,
                    tweet_data=tweet_data,
                    attachments_ids=[attachments_ids] if
                    attachments_ids else None,
                )
                # Add the tweet to the database

                session.add(tweet)
                await session.commit()
                tweet_id = tweet.tweet_id
            else:
                raise HTTPException(status_code=401,
                                     detail="Invalid API key")

    return {"result": True, "tweet_id": tweet_id}

@app.delete('/api/tweets/', tags=["TWEETS"])
async def delete_tweet(tweet_id: int, api_key: str):
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                tweet = await session.execute(
                    select(Tweets).filter(Tweets.tweet_id == tweet_id)
                )
                tweet = tweet.scalars().first()
                media = await session.execute(
                    select(Medias).filter(Medias.media_id.in_(tweet.attachments_ids))
                )
                if await check_belonging_tweet(tweet_id, api_key):
                    await session.delete(tweet)
                    await session.delete(media)
                    await session.commit()
                    return {"result": True}
                else:
                    raise HTTPException(status_code=404,
                                         detail="Tweet not found or "
                                                "not belonging to the user")
            else:
                raise HTTPException(status_code=401,
                                     detail="Invalid API key")

@app.post('/api/medias/', response_model=FileUploadResponse, tags=["TWEETS"])
async def upload_media(file: UploadFile = File(...)):
    # Handle media upload logic here
    file_name = file.filename
    file_body = file.file.read()
    content_type = file.content_type
    async with async_session() as session:
        media = Medias(file_name=file_name, file_body=file_body, content_type=content_type)
        session.add(media)
        await session.commit()
        return media.media_id

@app.post('/api/tweets/likes/', tags=["LIKES"])
async def like_tweet(tweet_id: int, api_key: str):
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                tweet = await session.execute(
                    select(Tweets).filter(Tweets.tweet_id == tweet_id)
                )
                tweet = tweet.scalars().first()
                if tweet:
                    user_id = await session.execute(
                        select(Users.user_id).where(Users.api_key == api_key)
                    )
                    user_id = user_id.scalars().first()
                    if not user_id in tweet.users_who_liked:
                        return await like(tweet, user_id)
                    else:
                        raise HTTPException(status_code=409,
                                             detail="User already liked the tweet")
                else:
                    raise HTTPException(status_code=404,
                                             detail="Tweet not found")
            else:
                raise HTTPException(status_code=401,
                                     detail="Invalid API key")

@app.delete('/api/tweets/likes/', tags=["LIKES"])
async def unlike_tweet(tweet_id: int, api_key: str):
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                tweet = await session.execute(
                    select(Tweets).filter(Tweets.tweet_id == tweet_id)
                )
                tweet = tweet.scalars().first()
                if tweet:
                    user_id = await session.execute(
                        select(Users.user_id).where(Users.api_key == api_key)
                    )
                    user_id = user_id.scalars().first()
                    if user_id in tweet.users_who_liked:
                        return await unlike(tweet, user_id)
                    else:
                        raise HTTPException(status_code=409,
                                             detail="User is not currently liking the tweet")
                else:
                    raise HTTPException(status_code=404,
                                             detail="Tweet not found")
            else:
                raise HTTPException(status_code=401,
                                     detail="Invalid API key")


@app.post('/api/users/follow/', tags=["FOLLOWS"])
async def follow_user(id_user: int, api_key: str):
    # Handle user following logic here
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                follower_id = await session.execute(
                    select(Users.user_id).where(Users.api_key == api_key)
                )
                follower_id = follower_id.scalars().first()
                following_id = id_user

                if follower_id == following_id:
                    raise HTTPException(status_code=400,
                                             detail="Cannot follow yourself")


                follows = await session.execute(
                    select(Follows).filter(
                    Follows.follower == follower_id,
                    Follows.following == following_id
                    ))
                follows = follows.scalars().first()
                if not follows:
                    session.add(Follows(follower=follower_id, following=following_id))
                    await session.commit()
                    return {"result": True}
                else:
                    raise HTTPException(status_code=409,
                                         detail="User is already following the specified user")
            else:
                raise HTTPException(status_code=401,
                                     detail="Invalid API key")

@app.delete('/api/users/follow/', tags=["FOLLOWS"])
async def unfollow_user(id_user: int, api_key: str):
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                follower_id = await session.execute(
                    select(Users.user_id).where(Users.api_key == api_key))
                follower_id = follower_id.scalars().first()
                following_id = id_user

                follow = await session.execute(
                    select(Follows).filter(
                        Follows.follower == follower_id,
                        Follows.following == following_id
                    )
                )
                follow = follow.scalars().first()

                if follow:
                    await session.delete(follow)
                    await session.commit()
                    return {"result": True}
                else:
                    raise HTTPException(status_code=404,
                                         detail="User is not following the specified user")
            else:
                raise HTTPException(status_code=401,
                                     detail="Invalid API key")

app.mount("/static", StaticFiles(directory="../client/static"), name="static")
app.mount("/js", StaticFiles(directory="../client/static/js"), name="js")
app.mount("/css", StaticFiles(directory="../client/static/css"), name="css")

if __name__ == "__main__":
    asyncio.run(create_tables())
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000)
