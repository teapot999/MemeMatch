import base64
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, make_response, render_template, redirect, abort, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import forms.meme
import forms.user
from data import db_session
from data.memes import Meme
from data.posts import Post
from data.users import User

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.json.ensure_ascii = False


# === Error handlers ===

@app.errorhandler(401)
def unauthorized(e):
    return render_template('401.html', title='Кто вы?'), 401


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', title='Пофиг, потеряли'), 404


# === In-app API ===

@app.route('/user_avatar/<int:user_id>')
def user_avatar(user_id):
    with db_session.create_session() as db_sess:
        user = db_sess.get(User, user_id)

        if not user:
            abort(404)

        if not user.picture:
            return app.send_static_file('img/default_avatar.jpg')

        response = make_response(user.picture)
        response.headers.set('Content-Type', 'image/jpeg')
        return response


@app.route('/meme_picture/<int:meme_id>')
def meme_picture(meme_id):
    with db_session.create_session() as db_sess:
        meme = db_sess.get(Meme, meme_id)

        if not meme or not meme.result_path:
            abort(404)

        response = make_response(open(meme.result_path, 'rb').read())
        response.headers.set('Content-Type', 'image/jpeg')
        return response


# ====== Pages ======

@app.route('/')
def index():
    with db_session.create_session() as db_sess:
        memes = db_sess.query(Post).all()
        return render_template('index.html', memes=memes)


# === Register and login ===

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.user.RegisterForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пользователь с таким юзернеймом уже есть уже есть")

            user = User(
                nickname=form.nickname.data,
                username=form.username.data,
                about=form.about.data,
                picture=form.picture.data.read()
            )
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            login_user(user, remember=form.remember_me.data)
            db_sess.close()
            return redirect('/')

    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.user.LoginForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            user = db_sess.query(User).filter(User.username == form.username.data).first()
            db_sess.close()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form)

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


# === Profile ===

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Профиль', user=current_user, is_owner=True)


@app.route('/profile/<int:user_id>')
def someones_profile(user_id):
    with db_session.create_session() as db_sess:
        user = db_sess.get(User, user_id)
        if not user:
            abort(404)

        is_owner = current_user.is_authenticated and user_id == current_user.id

        return render_template('profile.html', title='Профиль', user=user, is_owner=is_owner)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = forms.user.EditProfileForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('edit_profile.html', title='Регистрация',
                                       form=form,
                                       message="Этот юзернейм занят")

            current_user.username = form.username.data or current_user.username
            current_user.about = form.about.data or current_user.about
            current_user.nickname = form.nickname.data or current_user.nickname
            current_user.picture = form.picture.data.read() or current_user.picture

            db_sess.merge(current_user)

            db_sess.commit()
            db_sess.close()
            return redirect('/profile')

    return render_template('edit_profile.html', title='Редактирование профиля', form=form)


# === Memes ===

@app.route('/meme/create', methods=['GET', 'POST'])
def create_meme():
    form = forms.meme.MakingForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            meme_meta = request.form.get('meme_meta')

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

            _folderpath = os.path.join(app.root_path, 'static', 'uploads')
            source_filepath = os.path.join(_folderpath, f'sources/user{user_id}-meme{meme_id}.jpg')
            result_filepath = os.path.join(_folderpath, f'results/user{user_id}-meme{meme_id}.jpg')

            with open(source_filepath, 'wb') as source:
                source.write(meme_source)
            with open(result_filepath, 'wb') as result:
                result.write(meme_result)

            meme.source_path = source_filepath
            meme.result_path = result_filepath

            db_sess.merge(meme)
            db_sess.commit()

            return redirect('/')

    return render_template('meme_maker.html', title='Создание мема', form=form)


def main():
    db_session.global_init(os.getenv('DATABASE_PATH'), debug=False)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with db_session.create_session() as db_sess:
            user = db_sess.get(User, user_id)
            return user

    app.run()


if __name__ == '__main__':
    main()
