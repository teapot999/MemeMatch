from datetime import datetime
from secrets import token_hex

from flask_login import UserMixin
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    nickname = sa.Column(sa.String, nullable=True)
    about = sa.Column(sa.String, nullable=True)
    username = sa.Column(sa.String, index=True, unique=True, nullable=True)
    hashed_password = sa.Column(sa.String, nullable=True)
    created_date = sa.Column(sa.DateTime, default=datetime.now)
    picture = sa.Column(sa.String, nullable=True)
    api_key = sa.Column(sa.String, nullable=True, unique=True, index=True)

    memes = orm.relationship('Meme', back_populates='user')
    posts = orm.relationship('Post', back_populates='user')
    likes = orm.relationship('Like', back_populates='user')

    matches_as_author = orm.relationship('Match', foreign_keys='[Match.author_id]', back_populates='author')
    matches_as_matchman = orm.relationship('Match', foreign_keys='[Match.matchman_id]', back_populates='matchman')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def generate_api_key(self):
        self.api_key = token_hex(32)
        return self.api_key
