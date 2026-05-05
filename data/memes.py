import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Meme(SqlAlchemyBase):
    __tablename__ = 'memes'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    source_path = sa.Column(sa.String)
    result_path = sa.Column(sa.String)
    parent_meme_id = sa.Column(sa.Integer, nullable=True)
    meta = sa.Column(sa.JSON)

    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"))
    user = orm.relationship('User')
    post = orm.relationship('Post', back_populates='meme')
