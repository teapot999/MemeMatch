import os

from flask import Blueprint, render_template, redirect
from flask_login import login_user, logout_user, login_required

import forms.meme
import forms.user
from data import db_session
from data.users import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.user.RegisterForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('register.html',
                                       title='Регистрация',
                                       form=form,
                                       message="Пользователь с таким юзернеймом уже есть"
                                       )

            user = User(
                nickname=form.nickname.data,
                username=form.username.data,
                about=form.about.data,
            )
            db_sess.add(user)
            db_sess.flush()

            if pic_data := form.picture.data.read():
                avatar_path = os.path.join('static', 'avatars', f'user{user.id}.jpg')
                with open(avatar_path, 'wb') as avatar:
                    avatar.write(pic_data)
                user.picture = avatar_path

            user.set_password(form.password.data)
            db_sess.commit()
            login_user(user, remember=form.remember_me.data)
            return redirect('/')

    return render_template('register.html', title='Регистрация', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.user.LoginForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            user = db_sess.query(User).filter(User.username == form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form
                                   )

    return render_template('login.html', title='Авторизация', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")
