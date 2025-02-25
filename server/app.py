from typing import Dict, List, Tuple


from fastapi import FastAPI, HTTPException, UploadFile, Header
from fastapi.params import File
from sqlalchemy import ColumnElement
from sqlalchemy.future import select
from starlette.responses import Response


from models import Base, Tweets, Users, Follows, Medias
from schemas import CreateTweetSchema
from init_db import async_session
# Create a fastapi app
app = FastAPI()

async def check_api_key(api_key) -> bool:
    # Check if the API key is valid
    async with async_session() as session:
        return (
            await session.execute(select(Users.user_id).where(Users.api_key == api_key))
            is not None
        )


async def check_belonging_tweet(tweet_id, api_key) -> bool:
    async with async_session() as session:
        if await check_api_key(api_key):
            # Check if the tweet belongs to the specified user
            author_id = await session.execute(
                select(Tweets.author_id).where(Tweets.tweet_id == tweet_id)
            )
            author_id = author_id.scalars().first()
            user_id = await session.execute(
                select(Users.user_id).filter(Users.api_key == api_key)
            )
            user_id = user_id.scalars().first()
            return author_id == user_id



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


async def get_name(user_id: int) -> str:
    async with async_session() as session:
        name = await session.execute(
            select(Users.name).filter(Users.user_id == user_id)
        )
        name = name.scalars().first()
        return name


async def get_follows(user_id: int, _for: str) -> List:
    # Get all followers for the specified user
    async with async_session() as session:
        if _for == "followers":
            followers = await session.execute(
                select(Follows).filter(Follows.follower == user_id)
            )
            followers = followers.scalars().all()
            return followers

        elif _for == "following":
            following = await session.execute(
                select(Follows).filter(Follows.following == user_id)
            )
            following = following.scalars().all()
            return following


async def _get_user(user: Users) -> Dict:
    return {
        "result": True,
        "user": {
            "id": user.user_id,
            "name": user.name,
            "following": [
                {"id": follow.following, "name": await get_name(follow.following)}
                for follow in await get_follows(user.user_id, _for="following")
            ],
            "followers": [
                {"id": follow.follower, "name": await get_name(follow.follower)}
                for follow in await get_follows(user.user_id, _for="followers")
            ],
        },
    }

@app.get("/api/tweets", tags=["TWEETS"])
async def get_tweets(api_key: str = Header()) -> Dict or HTTPException:
    # Get all tweets for the specified user
    async with async_session() as session:
        if await check_api_key(api_key):
            tweets = await session.execute(select(Tweets))
            tweets = tweets.scalars().all()

            user_id = await session.execute(
                select(Users.user_id).where(Users.api_key == api_key)
            )
            user_id = user_id.scalars().first()

            follows = await get_follows(user_id=user_id, _for="followers")
            if follows:
                follows_list_ids = [followers.following for followers in follows]
                tweets = sorted(
                    tweets,
                    key=lambda tweet: sum(
                        1 if user_id in tweet.users_who_liked else 0
                        for user_id in follows_list_ids
                    ),
                    reverse=True,
                )

            try:
                tweet_responses = []
                for tweet in tweets:
                    tweet_response = {
                        "id": tweet.tweet_id,
                        "content": tweet.tweet_data,
                        "attachments": [
                            f"/api/medias/{i_attachment}"
                            for i_attachment in tweet.tweet_media_ids
                        ],
                        "author": {"id": tweet.author_id, "name": tweet.author_name},
                        "likes": [
                            {"user_id": user_id, "name": await get_name(user_id)}
                            for user_id in tweet.users_who_liked
                        ],
                    }
                    tweet_responses.append(tweet_response)

                return {"result": True, "tweets": tweet_responses}
            except Exception as e:
                return {
                    "result": False,
                    "error_type": str(type(e).__name__),
                    "error_message": str(e),
                }

        else:
            raise HTTPException(status_code=401, detail="Invalid API key")


async def get_media_path(media_id: int) -> Response:
    with async_session() as session:
        media = await session.execute(
            select(Medias).filter(Medias.media_id == media_id)
        )
        return Response(content=media.file_body, media_type="image/png")


@app.post("/api/tweets", tags=["TWEETS"])
async def create_tweet(tweet_data: CreateTweetSchema, api_key: str = Header()) -> Tuple[Dict, int] or HTTPException:
    async with async_session() as session:
        async with session.begin():
            # Check if the API key is valid
            if await check_api_key(api_key):
                # Get the author ID based on the API key
                _author_id = await session.execute(
                    select(Users.user_id).where(Users.api_key == api_key)
                )
                _author_id = _author_id.scalars().first()
                author_name = await session.execute(
                    select(Users.name).where(Users.user_id == _author_id)
                )
                author_name = author_name.scalars().first()

                # Create a new tweet object
                tweet = Tweets(
                    author_id=_author_id,
                    author_name=author_name,
                    tweet_data=tweet_data.tweet_data,
                    tweet_media_ids=tweet_data.tweet_media_ids,
                )
                # Add the tweet to the database

                session.add(tweet)
                await session.commit()
                tweet_id = tweet.tweet_id

            else:
                raise HTTPException(status_code=401, detail="Invalid API key")

    return {"result": True, "tweet_id": tweet_id}, 201


@app.delete("/api/tweets/{tweet_id}", tags=["TWEETS"])
async def delete_tweet(tweet_id: int, api_key: str = Header()) -> Tuple[Dict, int] or HTTPException:
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                tweet = await session.execute(
                    select(Tweets).filter(Tweets.tweet_id == tweet_id)
                )
                tweet = tweet.scalars().first()
                media = await session.execute(
                    select(Medias).filter(Medias.media_id.in_(tweet.tweet_media_ids))
                )
                media = media.scalars().all()
                if await check_belonging_tweet(tweet_id, api_key):
                    await session.delete(tweet)
                    if media:
                        for _media in media:
                            await session.delete(_media)
                    await session.commit()
                    return {"result": True}, 204
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="Tweet not found or " "not belonging to the user",
                    )
            else:
                raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/api/medias", tags=["MEDIAS"])
async def upload_media(file: UploadFile = File(...)) -> Dict or HTTPException:
    # Handle media upload logic here
    file_name = file.filename
    file_body = file.file.read()
    content_type = file.content_type
    async with async_session() as session:
        media = Medias(
            file_name=file_name, file_body=file_body, content_type=content_type
        )
        session.add(media)
        await session.commit()
        return {"result": True, "media_id": media.media_id}


@app.get("/api/medias/{media_id}", tags=["MEDIAS"])
async def get_media(media_id: int) -> Response or HTTPException:
    async with async_session() as session:
        media = await session.execute(
            select(Medias).filter(Medias.media_id == media_id)
        )
        media = media.scalars().first()
        if media:
            try:
                return Response(content=media.file_body, media_type=media.content_type)
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Error while retrieving media: {str(e)}"
                )
        else:
            raise HTTPException(status_code=404, detail="Media not found")


@app.post("/api/tweets/{tweet_id}/likes", tags=["LIKES"])
async def like_tweet(tweet_id: int, api_key: str = Header()) -> Response or HTTPException:
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
                        return await like(tweet, user_id), 201
                    else:
                        raise HTTPException(
                            status_code=409, detail="User already liked the tweet"
                        )
                else:
                    raise HTTPException(status_code=404, detail="Tweet not found")
            else:
                raise HTTPException(status_code=401, detail="Invalid API key")


@app.delete("/api/tweets/{tweet_id}/likes", tags=["LIKES"])
async def unlike_tweet(tweet_id: int, api_key: str = Header()) -> Response or HTTPException:
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
                        return await unlike(tweet, user_id), 204
                    else:
                        raise HTTPException(
                            status_code=409,
                            detail="User is not currently liking the tweet",
                        )
                else:
                    raise HTTPException(status_code=404, detail="Tweet not found")
            else:
                raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/api/users/{id_user}/follow", tags=["FOLLOWS"])
async def follow_user(id_user: int, api_key: str = Header()) -> Tuple[Dict, int] or HTTPException:
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
                    raise HTTPException(
                        status_code=400, detail="Cannot follow yourself"
                    )

                follows = await session.execute(
                    select(Follows).filter(
                        Follows.follower == follower_id,
                        Follows.following == following_id,
                    )
                )
                follows = follows.scalars().first()
                if not follows:
                    session.add(Follows(follower=follower_id, following=following_id))
                    await session.commit()
                    return {"result": True}, 201
                else:
                    raise HTTPException(
                        status_code=409,
                        detail="User is already following the specified user",
                    )
            else:
                raise HTTPException(status_code=401, detail="Invalid API key")


@app.delete("/api/users/{id_user}/follow", tags=["FOLLOWS"])
async def unfollow_user(id_user: int, api_key: str = Header()) -> Tuple[Dict, int] or HTTPException:
    async with async_session() as session:
        async with session.begin():
            if await check_api_key(api_key):
                follower_id = await session.execute(
                    select(Users.user_id).where(Users.api_key == api_key)
                )
                follower_id = follower_id.scalars().first()
                following_id = id_user

                follow = await session.execute(
                    select(Follows).filter(
                        Follows.follower == follower_id,
                        Follows.following == following_id,
                    )
                )
                follow = follow.scalars().first()

                if follow:
                    await session.delete(follow)
                    await session.commit()
                    return {"result": True}, 204
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="User is not following the specified user",
                    )
            else:
                raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/api/users/me", tags=["USERS"])
async def get_me(api_key: str = Header()) -> Dict or HTTPException:
    async with async_session() as session:
        user_id = await session.execute(
            select(Users.user_id).where(Users.api_key == api_key)
        )
        user_id = user_id.scalars().first()
        user = await session.execute(select(Users).filter(Users.user_id == user_id))
        user = user.scalars().first()
        if user:
            try:
                return await _get_user(user)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=404, detail="User not found")


@app.get("/api/users/{user_id}", tags=["USERS"])
async def get_user(user_id: int) -> Dict or HTTPException:
    async with async_session() as session:
        user = await session.execute(select(Users).filter(Users.user_id == user_id))
        user = user.scalars().first()
        if user:
            try:
                return await _get_user(user)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=404, detail="User not found")


# app.mount("/static", StaticFiles(directory="../client/static"), name="static")
# app.mount("/js", StaticFiles(directory="../client/static/js"), name="js")
# app.mount("/css", StaticFiles(directory="../client/static/css"), name="css")
