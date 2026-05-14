import base64
import json
import mimetypes
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, redirect, abort, request, url_for, send_from_directory, jsonify, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import joinedload

import forms.meme
import forms.user
from data import db_session
from data.likes import Like
from data.memes import Meme
from data.posts import Post
from data.users import User
from wrappers import api_or_login_required

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 7
app.json.ensure_ascii = False


# === Error handler ===

@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
@app.errorhandler(418)
@app.errorhandler(500)
def not_found(e):
    code = e.code
    titles = {
        401: 'Кто вы?',
        403: 'Доступ запрещён',
        404: 'Пофиг, потеряли',
        405: 'Убери свои шаловливые ручки',
        413: 'Слишком тяжёлый файл',
        418: 'Вы не чайник',
        500: 'Всё упало',
    }
    return render_template(f'error_pages/{code}.html', title=titles[code]), code


# === In-app API ===

@app.route('/user_avatar/<int:user_id>')
def user_avatar(user_id):
    with db_session.create_session() as db_sess:
        user = db_sess.get(User, user_id)

        if not user:
            abort(404)

        if not user.picture:
            directory = os.path.join(app.root_path, 'static', 'img')
            filename = 'default_avatar.jpg'
            full_file_path = os.path.join(directory, filename)

            if not os.path.exists(full_file_path):
                abort(404)

            response = send_from_directory(directory, filename)
            mtime = os.path.getmtime(full_file_path)

            response.headers['Cache-Control'] = 'no-cache, must-revalidate'
            response.set_etag(f"user-default-{mtime}")
            return response.make_conditional(request)

        clean_path = user.picture.replace('\\', '/')
        directory = os.path.join(app.root_path, os.path.dirname(clean_path))
        filename = os.path.basename(clean_path)

        full_file_path = os.path.join(directory, filename)
        if not os.path.exists(full_file_path):
            abort(404)

        response = send_from_directory(directory, filename)
        mtime = os.path.getmtime(full_file_path)

        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        response.set_etag(f"user-{user_id}-{mtime}")

        return response.make_conditional(request)


@app.route('/meme_picture/<int:meme_id>')
def meme_picture(meme_id):
    with db_session.create_session() as db_sess:
        meme = db_sess.get(Meme, meme_id)

        if not meme or not meme.result_path:
            abort(404)

        clean_path = meme.result_path.replace('\\', '/')

        if clean_path.startswith('static/'):
            clean_path = clean_path.replace('static/', '', 1)

        full_file_path = os.path.join(app.root_path, 'static', clean_path)

        if not os.path.exists(full_file_path):
            abort(404)

        response = send_from_directory(os.path.join(app.root_path, 'static'), clean_path)

        mime_type, _ = mimetypes.guess_type(full_file_path)
        if mime_type:
            response.headers['Content-Type'] = mime_type

        mtime = os.path.getmtime(full_file_path)

        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        response.set_etag(f"meme-{meme_id}-{mtime}")

        return response.make_conditional(request)


# === API ===

@app.route("/api/post/<int:post_id>/like", methods=['POST'])
@api_or_login_required
def like_post_api(post_id):
    with db_session.create_session() as db_sess:
        post = db_sess.get(Post, post_id)
        if not post:
            return jsonify({'status': 'error', 'message': 'The post is a lie'}), 404

        already_liked = db_sess.query(Like).filter(
            Like.user_id == g.api_user.id,
            Like.post_id == post_id
        ).first()

        if already_liked:
            db_sess.delete(already_liked)
            action = 'unliked'
        else:
            new_like = Like(user=db_sess.merge(g.api_user), post=post)
            db_sess.add(new_like)
            action = 'liked'

        db_sess.commit()

        likes_count = db_sess.query(Like).filter(Like.post_id == post_id).count()

    return jsonify({
        'status': 'ok',
        'action': action,
        'likes_count': likes_count
    })


@app.route("/api/post/<int:post_id>/delete", methods=['POST'])
@api_or_login_required
def delete_post_api(post_id):
    with db_session.create_session() as db_sess:
        post = db_sess.get(Post, post_id)
        if not post:
            return jsonify({'status': 'error', 'message': 'Post not found or already deleted'}), 404

        likes = db_sess.query(Like).filter(Like.post_id == post_id).all()
        for like in likes:
            db_sess.delete(like)

        meme = db_sess.get(Meme, post.meme_id)

        for path in [meme.source_path, meme.result_path]:
            if path and os.path.exists(path):
                os.remove(path)

        db_sess.delete(meme)
        db_sess.delete(post)

        db_sess.commit()

        return jsonify({'status': 'ok'})


# ====== Pages ======

@app.route('/')
def index():
    with db_session.create_session() as db_sess:
        posts = db_sess.query(Post).order_by(Post.created_date.desc()).all()
        return render_template('index.html', posts=posts)


# === Register and login ===

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.user.RegisterForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пользователь с таким юзернеймом уже есть")

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
@app.route('/profile/<user_id>')
def someones_profile(user_id):
    with db_session.create_session() as db_sess:
        if isinstance(user_id, int):
            user = db_sess.get(User, user_id)
        else:
            user = db_sess.query(User).filter(User.username == user_id).first()
        if not user:
            abort(404)

        is_owner = current_user.is_authenticated and user.id == current_user.id

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


# === Memes ===

@app.route('/meme/create', methods=['GET', 'POST'])
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

            return redirect(url_for('upload_meme', meme_id=meme_id))

    return render_template(
        'meme_maker.html',
        page_title='Создание мема',
        title='1. Создание мема',
        form=form)


@app.route('/meme/<int:meme_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_meme(meme_id):
    with (db_session.create_session() as db_sess):
        meme = db_sess.query(Meme).options(joinedload(Meme.user)).get(meme_id)
        if not meme:
            abort(404)

        is_uploading_by_current_user = (meme.user_id == current_user.id)
        is_published = db_sess.query(Post.meme_id).filter(Post.meme_id == meme_id).first() is not None
        if not is_uploading_by_current_user or is_published:
            abort(403)

        form = forms.meme.UploadingForm()
        if form.validate_on_submit():
            post = Post(
                user=db_sess.merge(current_user),
                meme=meme,
                title=form.title.data,
                description=form.descr.data)
            db_sess.add(post)
            db_sess.commit()

            return redirect('/')

    return render_template(
        'meme_uploader.html',
        page_title='Создание мема',
        title='2. Выкладывание мема',
        form=form,
        meme=meme
    )


def main():
    db_session.global_init(os.getenv('DATABASE_PATH'), debug=False)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with db_session.create_session() as db_sess:
            return db_sess.get(User, user_id)

    host = '0.0.0.0' if os.getenv('HOST') else '127.0.0.1'
    port = int(os.getenv('PORT', 5000))

    app.run(host=host, port=port)


if __name__ == '__main__':
    main()
