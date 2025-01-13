from pydantic import BaseModel
from typing import Optional


class CreateTweetSchema(BaseModel):
    tweet_data: str
    #tweet_media_ids: Optional[list[int]] = None

class TweetSchema(CreateTweetSchema):
    tweet_id: int
    likes: int
    users_who_liked: list