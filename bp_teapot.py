import os

from flask import Blueprint, redirect, abort

from data import db_session
from data.likes import Like
from data.matches import Match
from data.memes import Meme
from data.users import User
from wrappers import admin_only

teapot_bp = Blueprint('teapot', __name__)


@teapot_bp.route('/user/<int:user_id>/block')
@admin_only
def block_author(user_id):
    if user_id == int(os.getenv('ADMIN_ID'), 1):
        abort(400)
    with db_session.create_session() as db_sess:
        user = db_sess.get(User, user_id)
        if not user:
            abort(404)

        for post in user.posts:
            meme = post.meme
            if meme.source_path:
                source_usage_count = db_sess.query(Meme).filter(Meme.source_path == meme.source_path).count()
                if source_usage_count <= 1 and os.path.exists(meme.source_path):
                    os.remove(meme.source_path)
            if meme.result_path:
                if os.path.exists(meme.result_path):
                    os.remove(meme.result_path)
            db_sess.delete(meme)

            likes = db_sess.query(Like).filter(Like.post_id == post.id).all()
            for like in likes:
                db_sess.delete(like)

            matches = db_sess.query(Match).filter((Match.post_id == post.id) | (Match.new_post_id == post.id)).all()
            for match in matches:
                db_sess.delete(match)

            db_sess.delete(post)

        db_sess.delete(user)

        db_sess.commit()

        return redirect('/')
