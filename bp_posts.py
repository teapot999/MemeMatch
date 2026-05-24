import base64
import json
import os

from flask import Blueprint, render_template, redirect, abort, request, url_for
from flask_login import login_required, current_user

import forms.meme
import forms.user
from data import db_session
from data.memes import Meme
from data.posts import Post
from wrappers import current_user_only

posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/post/<int:post_id>')
def show_post(post_id):
    with db_session.create_session() as db_sess:
        post = db_sess.get(Post, post_id)
        if not post:
            abort(404)

        return render_template('view_post.html', title='Просмотр поста', original_post=post)


@posts_bp.route('/post/<int:post_id>/match-from/<int:matched_post_id>')
def show_original_post(post_id, matched_post_id):
    with db_session.create_session() as db_sess:
        original_post = db_sess.get(Post, post_id)
        if not original_post or not original_post.matches_from_this:
            abort(404)
        matched_post = db_sess.get(Post, matched_post_id)
        if not matched_post or not matched_post.match_result:
            abort(404)

        return render_template(
            'view_post.html',
            title='Просмотр оригинала',
            original_post=original_post,
            matched_post=matched_post
        )


@posts_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@current_user_only(Post, url_param='post_id')
def edit_post(post_id):
    with db_session.create_session() as db_sess:
        post = db_sess.get(Post, post_id)
        if not post or not post.meme:
            abort(404)

        meme = post.meme

        form = forms.meme.EditingForm()
        if form.validate_on_submit():
            meme.meta = json.loads(request.form.get('meme_meta', '{}'))
            db_sess.merge(meme)

            meme_result_data = request.form.get('meme_result')
            if meme_result_data:
                _, b64picture = meme_result_data.split(',', 1)
                meme_result = base64.b64decode(b64picture)
                with open(meme.result_path, 'wb') as result:
                    result.write(meme_result)

            db_sess.commit()

            return redirect(url_for('memes.upload_meme', meme_id=meme.id, editing=True))

        return render_template(
            'meme_editor.html',
            title='Редактирование мема',
            form=form,
            meme=meme
        )


@posts_bp.route('/post/<int:post_id>/match', methods=['GET', 'POST'])
@login_required
def make_match_with_post(post_id):
    with db_session.create_session() as db_sess:
        post = db_sess.get(Post, post_id)
        if not post or not post.meme:
            abort(404)

        original_meme = db_sess.query(Meme).filter(Meme.post_id == post_id).first()

        form = forms.meme.EditingForm()
        if form.validate_on_submit():
            meme_meta = json.loads(request.form.get('meme_meta', '{}'))

            meme = Meme(
                meta=meme_meta,
                user=current_user,
                parent_meme_id=original_meme.id
            )
            db_sess.add(meme)
            db_sess.flush()
            meme_id = meme.id
            user_id = meme.user_id

            meme_result_data = request.form.get('meme_result')
            if meme_result_data:
                _, b64picture = meme_result_data.split(',', 1)
                meme_result = base64.b64decode(b64picture)

            _folderpath = os.path.join('static', 'uploads')
            result_filepath = os.path.join(_folderpath, 'results', f'user{user_id}-meme{meme_id}.jpg')

            source_filepath = original_meme.source_path

            with open(result_filepath, 'wb') as result:
                result.write(meme_result)

            meme.source_path = source_filepath
            meme.result_path = result_filepath

            db_sess.commit()

            return redirect(url_for('memes.upload_meme', meme_id=meme_id, matching=post.id))

        return render_template(
            'meme_editor.html',
            title='Создание мэтча',
            meme=original_meme,
            form=form
        )
