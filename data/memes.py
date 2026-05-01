import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Meme(SqlAlchemyBase):
    __tablename__ = 'memes'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String, nullable=True)
    description = sa.Column(sa.String, nullable=True)
    picture = sa.Column(sa.BLOB)
    created_date = sa.Column(sa.DateTime, default=lambda d: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    project_type = sa.Column(sa.String)
    meta = sa.Column(sa.JSON)
    likes = sa.Column(sa.JSON, nullable=True, default=[])
    matches = sa.Column(sa.JSON, nullable=True, default=[])

    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"))
    user = orm.relationship('User')
