import sqlalchemy as sa
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class DemikFrame(SqlAlchemyBase):
    __tablename__ = 'demik_frames'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String)
    description = sa.Column(sa.String, nullable=True)

    meme_id = sa.Column(sa.Integer, sa.ForeignKey('memes.id'))
    meme = orm.relationship('Meme', back_populates='demik_frame', foreign_keys='[Meme.id]', uselist=False)
