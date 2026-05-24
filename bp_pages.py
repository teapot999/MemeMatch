from flask import Blueprint, render_template

from data import db_session
from data.posts import Post

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    with db_session.create_session() as db_sess:
        posts = db_sess.query(Post).order_by(Post.created_date.desc()).all()
        return render_template('index.html', posts=posts)


@pages_bp.route('/healthcheck')
def healthcheck():
    return 'Hello Server!'
