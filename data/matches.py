import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Matches(SqlAlchemyBase):
    __tablename__ = 'matches'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    author_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"))
    matchman_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"))
    post_id = sa.Column(sa.Integer, sa.ForeignKey("posts.id"))
    match_id = sa.Column(sa.Integer, sa.ForeignKey("posts.id"))


