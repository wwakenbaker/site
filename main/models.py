from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, Integer, String, ForeignKey


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(primary_key=True)

class Tweet(Base):
    __tablename__ = 'tweets'

    tweet_id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    content: Mapped[str] = mapped_column(String)
    likes: Mapped[int] = mapped_column(Integer)
    # media: Mapped[ARRAY[int]] = mapped_column(Integer)

class Follow(Base):
    __tablename__ = 'follows'

    follow_id: Mapped[int] = mapped_column(primary_key=True)
    follower: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    following: Mapped[int] = mapped_column(ForeignKey('users.user_id'))