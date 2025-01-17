from pydantic import BaseModel
from typing import List


class CreateTweetSchema(BaseModel):
    tweet_data: str
    attachments: List[int]

class TweetSchema(CreateTweetSchema):
    tweet_id: int
    author_name: str
    likes: int
    users_who_liked: list

class FileUploadResponse(BaseModel):
    file_name: str
    content_type: str
    file_body: bytes
