from pydantic import BaseModel

class CreateTweetSchema(BaseModel):
    author_key: str
    content: str

class TweetSchema(CreateTweetSchema):
    tweet_id: int
    likes: int