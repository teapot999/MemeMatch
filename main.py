import base64
import json
import mimetypes
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, redirect, abort, request, url_for, send_from_directory, jsonify, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from sqlalchemy import select
from sqlalchemy.orm import joinedload

import forms.meme
import forms.user
from data import db_session
from data.likes import Like
from data.matches import Match
from data.memes import Meme
from data.posts import Post
from data.users import User
from wrappers import current_user_only, api_only, api_or_login, admin_only

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 7
app.jinja_env.globals['Post'] = Post
app.json.ensure_ascii = False

csrf = CSRFProtect(app)

db_path = os.getenv('DATABASE_PATH')
if not db_path:
    db_dir = os.path.join(app.root_path, 'db')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'blogs.db')

db_session.global_init(db_path, debug=False)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    with db_session.create_session() as db_sess:
        return db_sess.get(User, user_id)


# === Error handler ===

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
@app.errorhandler(418)
@app.errorhandler(500)
def error_handler(e):
    code = e.code
    titles = {
        400: 'Невалидный запрос',
        401: 'Кто вы?',
        403: 'Доступ запрещён',
        404: 'Пофиг, потеряли',
        405: 'Убери свои шаловливые ручки',
        413: 'Слишком тяжёлый файл',
        418: 'Вы не чайник',
        500: 'Всё упало',
    }

    if request.path.startswith('/api'):
        return jsonify({'status': 'error', 'code': code, 'message': e.description})

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

        match request.args.get('type', 'result'):
            case 'source':
                meme_path = meme.source_path
                download_filename = f"MemeMatch-post-{meme_id}-source.jpg"
            case 'result':
                meme_path = meme.result_path
                download_filename = f"MemeMatch-post-{meme_id}.jpg"
            case _:
                abort(400)

        if not meme or not meme_path:
            abort(404)

        clean_path = meme_path.replace('\\', '/')

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

        if request.args.get('download'):
            response.headers['Content-Disposition'] = f'attachment; filename="{download_filename}"'

        return response.make_conditional(request)


# === API ===

def clear_crashed_bytes(dct):
    for k, v in dct.items():
        if isinstance(v, dict):
            dct[k] = clear_crashed_bytes(v)
        if not isinstance(v, str):
            continue
        dct[k] = v.encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore')
    return dct


@app.route('/api/<entity_type>/s')
@api_only
@csrf.exempt
def get_entities_list_api(entity_type):
    with db_session.create_session() as db_sess:
        match entity_type:
            case 'user':
                ids = db_sess.scalars(select(User.id).order_by(User.id)).all()
            case 'post':
                ids = db_sess.scalars(select(Post.id).order_by(Post.created_date.desc())).all()
            case 'meme':
                ids = db_sess.scalars(select(Meme.id).order_by(Meme.id.desc())).all()
            case _:
                return jsonify({'status': 'error',
                                'message': f'Unknown entity type: {entity_type}. Allowed: user, post, meme.'}), 400

        return jsonify({'status': 'ok', 'count': len(ids), f'entity_ids': ids, 'type': entity_type})


@app.route('/api/<entity_type>/<int:entity_id>')
@api_or_login
@csrf.exempt
def get_entity_api(entity_type, entity_id):
    with db_session.create_session() as db_sess:
        match entity_type:
            case 'user':
                obj = db_sess.get(User, entity_id)
                if not obj:
                    return jsonify({'status': 'error', 'message': f'The {entity_type} №{entity_id} is a lie'}), 404

                params = ['id', 'username', 'nickname', 'about', 'created_date']

                user_posts = db_sess.scalars(select(Post.id).filter(Post.author_id == entity_id)).all()
                user_has_avatar = obj.picture is not None
                additional = {'posts': user_posts, 'picture': user_has_avatar}
            case 'meme':
                obj = db_sess.get(Meme, entity_id)
                params = ['id', 'parent_meme_id', 'user_id', 'post_id', 'meta']
                additional = {}
            case 'post':
                obj = db_sess.get(Post, entity_id)
                if not obj:
                    return jsonify({'status': 'error', 'message': f'The {entity_type} №{entity_id} is a lie'}), 404

                params = ['id', 'title', 'description', 'created_date', 'author_id']

                post_likes = db_sess.scalars(
                    select(Like.user_id).filter(Like.post_id == entity_id).order_by(Like.user_id)).all()

                post_meme_id = obj.meme.id if obj.meme else None

                post_matches_from_this = db_sess.scalars(
                    select(Match.new_post_id).filter(Match.post_id == entity_id)
                ).all()

                parent_match = db_sess.query(Match).filter(Match.new_post_id == entity_id).first()
                post_match_result_id = parent_match.post_id if parent_match else None

                additional = {
                    'likes': post_likes,
                    'meme_id': post_meme_id,
                    'matches_from_this': post_matches_from_this,
                    'match_result': post_match_result_id
                }
            case _:
                return jsonify({'status': 'error',
                                'message': f'Unknown entity type: {entity_type}. Allowed types: user, post, meme.'}), 400
        if not obj:
            return jsonify({'status': 'error', 'message': f'The {entity_type} №{entity_id} is a lie'}), 404

        data = clear_crashed_bytes(obj.to_dict(only=params))
        data.update(additional)

        return jsonify({'status': 'ok', **data})


@app.route('/api/<entity_type>/<int:entity_id>/picture')
@api_only
@csrf.exempt
def get_entity_picture_api(entity_type, entity_id):
    with db_session.create_session() as db_sess:
        match entity_type:
            case 'user':
                obj = db_sess.get(User, entity_id)
                if not obj:
                    return jsonify({'status': 'error', 'message': f'The {entity_type} №{entity_id} is a lie'}), 404

                pic_path = obj.picture
            case 'meme':
                obj = db_sess.get(Meme, entity_id)
                if not obj:
                    return jsonify({'status': 'error', 'message': f'The {entity_type} №{entity_id} is a lie'}), 404

                pic_type = request.args.get('type', 'result')
                match pic_type:
                    case 'source':
                        pic_path = obj.source_path
                    case 'result':
                        pic_path = obj.result_path
                    case _:
                        return jsonify({'status': 'error',
                                        'message': f'Invalid value of parameter "type": {pic_type}. Supported types : source, result.'}), 400
            case 'post':
                post = db_sess.get(Post, entity_id)
                if not post:
                    return jsonify({'status': 'error', 'message': f'The {entity_type} №{entity_id} is a lie'}), 404

                obj = post.meme
                pic_type = request.args.get('type', 'result')
                match pic_type:
                    case 'source':
                        pic_path = obj.source_path
                    case 'result':
                        pic_path = obj.result_path
                    case _:
                        return jsonify({'status': 'error',
                                        'message': f'Invalid value of parameter "type": {pic_type}. Supported types : source, result.'}), 400
            case _:
                return jsonify({'status': 'error',
                                'message': f'Unknown entity type: {entity_type}. Allowed types: user, post, meme.'}), 400
        if not obj:
            return jsonify({'status': 'error', 'message': f'The {entity_type} #{entity_id} is a lie'}), 404
        if not pic_path:
            return jsonify(
                {'status': 'error', 'message': f'The picture for the {entity_type} №{entity_id} is a lie'}), 404

        clean_path = pic_path.replace('\\', '/')

        if clean_path.startswith('static/'):
            clean_path = clean_path.replace('static/', '', 1)

        full_file_path = os.path.join(app.root_path, 'static', clean_path)

        if not os.path.exists(full_file_path):
            return jsonify(
                {'status': 'error', 'message': f'There is no file satisfied at {entity_type} №{entity_id}.'}), 404

        response = send_from_directory(os.path.join(app.root_path, 'static'), clean_path)

        mime_type, _ = mimetypes.guess_type(full_file_path)
        if mime_type:
            response.headers['Content-Type'] = mime_type

        mtime = os.path.getmtime(full_file_path)

        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        response.set_etag(f"meme-{entity_type}-{entity_id}-{mtime}")

        return response.make_conditional(request)


@app.route("/api/post/<int:post_id>/like", methods=['PUT'])
@api_or_login
@csrf.exempt
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

    return jsonify({'status': 'ok', 'action': action, 'likes_count': likes_count})


@app.route("/api/post/<int:post_id>", methods=['DELETE'])
@api_or_login
@csrf.exempt
def delete_post_api(post_id):
    with db_session.create_session() as db_sess:
        post = db_sess.get(Post, post_id)
        if not post:
            if current_user.is_authenticated:
                abort(404)
            return jsonify({'status': 'error', 'message': 'Post not found or already deleted'}), 404
        if post.author_id != g.api_user.id and str(g.api_user.id) != os.getenv('ADMIN_ID'):
            if current_user.is_authenticated:
                abort(403)
            return jsonify({'status': 'error', 'message': 'Post does not belong to you'}), 403

        meme = post.meme

        if meme.source_path:
            source_usage_count = db_sess.query(Meme).filter(Meme.source_path == meme.source_path).count()
            if source_usage_count <= 1 and os.path.exists(meme.source_path):
                os.remove(meme.source_path)

        if meme.result_path:
            if os.path.exists(meme.result_path):
                os.remove(meme.result_path)

        likes = db_sess.query(Like).filter(Like.post_id == post_id).all()
        for like in likes:
            db_sess.delete(like)

        matches = db_sess.query(Match).filter((Match.post_id == post_id) | (Match.new_post_id == post_id)).all()
        for match in matches:
            db_sess.delete(match)

        db_sess.delete(meme)
        db_sess.delete(post)
        db_sess.commit()

        return jsonify({'status': 'ok'})


# === My-API ===

@app.route("/my-api/get-key")
@login_required
def generate_user_api_key():
    with db_session.create_session() as db_sess:
        raw_api_key = current_user.generate_api_key()

        db_sess.merge(current_user)
        db_sess.commit()

        return render_template('api_new_key.html', api_key=raw_api_key, title='Новый API-ключ')


@app.route("/my-api/get-key/force-trying")
@login_required
def get_user_api_key():
    with db_session.create_session() as db_sess:
        raw_api_key = current_user.generate_api_key()

        if db_sess.get(User, current_user.id).hashed_api_key:
            return render_template('api_reject_key.html', title='Ключ уже сгенерирован')

        db_sess.merge(current_user)
        db_sess.commit()

        return render_template('api_new_key.html', api_key=raw_api_key, title='Новый API-ключ')


# ====== Pages ======

@app.route('/')
def index():
    with db_session.create_session() as db_sess:
        posts = db_sess.query(Post).order_by(Post.created_date.desc()).all()
        return render_template('index.html', posts=posts)


@app.route('/healthcheck')
def healthcheck():
    return 'Hello Server!'


# === Register and login ===

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.user.RegisterForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('register.html',
                                       title='Регистрация',
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
    with db_session.create_session() as db_sess:
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        posts = db_sess.query(Post).filter(Post.author_id == user.id).order_by(Post.created_date.desc()).all()
        return render_template('profile.html', title='Профиль', user=user, is_owner=True, posts=posts)


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
        posts = db_sess.query(Post).filter(Post.author_id == user.id).order_by(Post.created_date.desc()).all()

        return render_template('profile.html', title='Профиль', user=user, is_owner=is_owner, posts=posts)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = forms.user.EditProfileForm()
    if form.validate_on_submit():
        with db_session.create_session() as db_sess:
            if db_sess.query(User).filter(User.username == form.username.data).first():
                return render_template('edit_profile.html',
                                       title='Регистрация',
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

    return render_template('meme_maker.html',
                           title='Создание мема',
                           form=form)


@app.route('/meme/<int:meme_id>/upload', methods=['GET', 'POST'])
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


@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
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

            return redirect(url_for('upload_meme', meme_id=meme.id, editing=True))

        return render_template('meme_editor.html',
                               title='Редактирование мема',
                               form=form,
                               meme=meme)


@app.route('/post/<int:post_id>/match', methods=['GET', 'POST'])
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

            return redirect(url_for('upload_meme', meme_id=meme_id, matching=post.id))

        return render_template(
            'meme_editor.html',
            title='Создание мэтча',
            meme=original_meme,
            form=form)


# === Teapot functions ===

@app.route('/user/<int:user_id>/block')
@admin_only
def block_author(user_id):
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


if __name__ == '__main__':
    host = '0.0.0.0' if os.getenv('HOST') else '127.0.0.1'
    port = int(os.getenv('PORT', 5000))

    app.run(host=host, port=port)
