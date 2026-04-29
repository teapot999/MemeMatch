from datetime import timedelta

from flask import Flask, make_response, render_template, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import forms.user
from data import db_session
from data.users import User

app = Flask(__name__)
app.config['SECRET_KEY'] = open('secret_key.txt').read().strip()
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.json.ensure_ascii = False


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', title='Пофиг, потеряли'), 404


@app.route('/user_avatar/<int:user_id>')
def user_avatar(user_id):
    db_sess = db_session.create_session()
    db_sess.close()
    user = db_sess.get(User, user_id)

    if not user or not user.picture:
        return app.send_static_file('img/default_avatar.jpg')

    response = make_response(user.picture)
    response.headers.set('Content-Type', 'image/jpeg')
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.user.RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
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
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        db_sess.close()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Профиль')


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = forms.user.EditProfileForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def main():
    db_session.global_init("db/table.db", debug=False)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        db_sess = db_session.create_session()
        user = db_sess.get(User, user_id)
        db_sess.close()
        return user

    app.run()


if __name__ == '__main__':
    main()
