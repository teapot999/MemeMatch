import base64
import json
import os

from flask import Blueprint, render_template, redirect, abort, request, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

import forms.meme
import forms.user
from data import db_session
from data.matches import Match
from data.memes import Meme
from data.posts import Post

memes_bp = Blueprint('memes', __name__)


@memes_bp.route('/meme/create', methods=['GET', 'POST'])
@login_required
def create_meme():
    form = forms.meme.MakingForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            meme_meta = json.loads(request.form.get('meme_meta', '{}'))

            meme = Meme(
                meta=meme_meta,
                user=current_user,
            )
            db_sess.add(meme)
            db_sess.flush()
            meme_id = meme.id
            user_id = meme.user_id

            meme_source = form.picture.data.read()
            meme_result_data = request.form.get('meme_result')
            if meme_result_data:
                _, b64picture = meme_result_data.split(',', 1)
                meme_result = base64.b64decode(b64picture)

            _folderpath = os.path.join('static', 'uploads')
            source_filepath = os.path.join(_folderpath, 'sources', f'user{user_id}-meme{meme_id}.jpg')
            result_filepath = os.path.join(_folderpath, 'results', f'user{user_id}-meme{meme_id}.jpg')

            with open(source_filepath, 'wb') as source:
                source.write(meme_source)
            with open(result_filepath, 'wb') as result:
                result.write(meme_result)

            meme.source_path = source_filepath
            meme.result_path = result_filepath

            db_sess.commit()

            return redirect(url_for('memes.upload_meme', meme_id=meme_id))

    return render_template(
        'meme_maker.html',
        title='Создание мема',
        form=form
    )


@memes_bp.route('/meme/<int:meme_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_meme(meme_id):
    with db_session.create_session() as db_sess:
        meme = db_sess.query(Meme).options(joinedload(Meme.user)).get(meme_id)
        if not meme:
            abort(404)

        is_uploading_by_current_user = (meme.user_id == current_user.id)
        is_published = meme.post_id is not None
        is_editing = request.args.get('editing')

        matching_post_id = request.args.get('matching')

        if not is_uploading_by_current_user or (is_published and not is_editing):
            abort(403)

        current_post = None
        if is_published:
            current_post = db_sess.query(Post).filter(Post.id == meme.post_id).first()

        form = forms.meme.UploadingForm()
        if form.validate_on_submit():
            if is_editing and current_post:
                current_post.title = form.title.data
                current_post.description = form.descr.data
            else:
                post = Post(
                    user=db_sess.merge(current_user),
                    title=form.title.data,
                    description=form.descr.data
                )
                post.meme = meme
                db_sess.add(post)
                db_sess.flush()

                if matching_post_id:
                    new_match = Match(
                        author_id=db_sess.query(Post).filter(Post.id == matching_post_id).first().author_id,
                        matchman_id=current_user.id,
                        post_id=int(matching_post_id),
                        new_post_id=post.id
                    )
                    db_sess.add(new_match)

            db_sess.commit()
            return redirect('/')

        if is_editing and current_post and request.method == 'GET':
            form.title.data = current_post.title
            form.descr.data = current_post.description

        return render_template(
            'meme_uploader.html',
            title='Выкладывание мема',
            form=form,
            meme=meme,
            post=current_post,
        )
