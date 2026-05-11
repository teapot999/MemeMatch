from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Post(SqlAlchemyBase):
    __tablename__ = 'posts'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String)
    description = sa.Column(sa.String, nullable=True)
    created_date = sa.Column(sa.DateTime, default=datetime.now)

    likes = orm.relationship('Like', back_populates='post')
    matches_from_this = orm.relationship('Match', back_populates='original_post', foreign_keys='[Match.post_id]')
    match_result = orm.relationship('Match', back_populates='new_post', foreign_keys='[Match.new_post_id]', uselist=False)

    author_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    user = orm.relationship('User', back_populates='posts')
    meme_id = sa.Column(sa.Integer, sa.ForeignKey('memes.id'))
    meme = orm.relationship('Meme', back_populates='post')
