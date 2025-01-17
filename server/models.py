from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey, LargeBinary


class Base(DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    api_key: Mapped[str] = mapped_column(String)

class Tweets(Base):
    __tablename__ = 'tweets'

    tweet_id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    author_name: Mapped[str] = mapped_column(ForeignKey('users.name'))
    tweet_data: Mapped[str] = mapped_column(String)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    users_who_liked: Mapped[ARRAY | list] = mapped_column(ARRAY(Integer), default=list)
    attachments_ids: Mapped[ARRAY | list] = mapped_column(ARRAY(Integer), default=list)

class Follows(Base):
    __tablename__ = 'follows'

    follow_id: Mapped[int] = mapped_column(primary_key=True)
    follower: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    following: Mapped[int] = mapped_column(ForeignKey('users.user_id'))

class Medias(Base):
    __tablename__ ='medias'

    media_id: Mapped[int] = mapped_column(primary_key=True)
    file_body: Mapped[str] = mapped_column(LargeBinary)
    file_name: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)

