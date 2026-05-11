import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Match(SqlAlchemyBase):
    __tablename__ = 'matches'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    author_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    matchman_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    post_id = sa.Column(sa.Integer, sa.ForeignKey('posts.id'))
    new_post_id = sa.Column(sa.Integer, sa.ForeignKey('posts.id'))

    author = orm.relationship('User', foreign_keys=[author_id], back_populates='matches_as_author')
    matchman = orm.relationship('User', foreign_keys=[matchman_id], back_populates='matches_as_matchman')

    original_post = orm.relationship('Post', foreign_keys=[post_id], back_populates='matches_from_this')
    new_post = orm.relationship('Post', foreign_keys=[new_post_id], back_populates='match_result')
