from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey

class Base(DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(primary_key=True)
    api_key: Mapped[str] = mapped_column(String)

class Tweets(Base):
    __tablename__ = 'tweets'

    tweet_id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    content: Mapped[str] = mapped_column(String)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    # media: Mapped[ARRAY[int]] = mapped_column(Integer, default=None)

class Follows(Base):
    __tablename__ = 'follows'

    follow_id: Mapped[int] = mapped_column(primary_key=True)
    follower: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    following: Mapped[int] = mapped_column(ForeignKey('users.user_id'))