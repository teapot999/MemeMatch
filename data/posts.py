from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Post(SqlAlchemyBase):
    __tablename__ = 'posts'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String, nullable=True)
    description = sa.Column(sa.String, nullable=True)
    created_date = sa.Column(sa.DateTime, default=datetime.now)
    likes = sa.Column(sa.JSON, nullable=True, default=[])
    matches = sa.Column(sa.JSON, nullable=True, default=[])

    author_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"))
    user = orm.relationship('User')
    meme_id = sa.Column(sa.Integer, sa.ForeignKey("memes.id"))
    meme = orm.relationship('Meme', back_populates='post')
