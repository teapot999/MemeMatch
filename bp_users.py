import os

from flask import Blueprint, render_template, redirect, abort
from flask_login import login_required, current_user

import forms.meme
import forms.user
from data import db_session
from data.posts import Post
from data.users import User

user_bp = Blueprint('users', __name__)


@user_bp.route('/profile')
@user_bp.route('/user')
@login_required
def profile():
    with db_session.create_session() as db_sess:
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        posts = db_sess.query(Post).filter(Post.author_id == user.id).order_by(Post.created_date.desc()).all()
        return render_template('profile.html', title='Профиль', user=user, is_owner=True, posts=posts)


@user_bp.route('/profile/<int:user_id>')
@user_bp.route('/profile/<user_id>')
@user_bp.route('/user/<int:user_id>')
@user_bp.route('/user/<user_id>')
def someones_profile(user_id):
    with db_session.create_session() as db_sess:
        if isinstance(user_id, int):
            user = db_sess.get(User, user_id)
        else:
            user = db_sess.query(User).filter(User.username == user_id).first()
        if not user:
            abort(404)

        is_owner = current_user.is_authenticated and user.id == current_user.id
        posts = db_sess.query(Post).filter(Post.author_id == user.id).order_by(Post.created_date.desc()).all()

        return render_template('profile.html', title='Профиль', user=user, is_owner=is_owner, posts=posts)


@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@user_bp.route('/user/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = forms.user.EditProfileForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('edit_profile.html',
                                       title='Регистрация',
                                       form=form,
                                       message="Этот юзернейм занят"
                                       )

            current_user.username = form.username.data or current_user.username
            current_user.about = form.about.data or current_user.about
            current_user.nickname = form.nickname.data or current_user.nickname

            if pic_data := form.picture.data.read():
                avatar_path = os.path.join('static', 'avatars', f'user{current_user.id}.jpg')
                with open(avatar_path, 'wb') as avatar:
                    avatar.write(pic_data)
                current_user.picture = avatar_path or current_user.picture

            db_sess.merge(current_user)

            db_sess.commit()
            db_sess.close()
            return redirect('/profile')

    return render_template('edit_profile.html', title='Редактирование профиля', form=form)
