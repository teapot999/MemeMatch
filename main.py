import flask as fl
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import forms
from data import db_session
from data.users import User

app = fl.Flask(__name__)
app.config['SECRET_KEY'] = open('secret_key.txt').read().strip()


@app.errorhandler(404)
def page_not_found(e):
    return fl.render_template('404.html', title='Пофиг, потеряли')


@app.route('/')
def index():
    name = 'Анонимус'
    if current_user.is_authenticated:
        name = current_user.name
    return fl.render_template('index.html', name=name)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.user.RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return fl.render_template('register.html', title='Регистрация',
                                      form=form,
                                      message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.username == form.username.data).first():
            return fl.render_template('register.html', title='Регистрация',
                                      form=form,
                                      message="Такой пользователь уже есть")
        user = User(
            name=form.nickname.data,
            username=form.username.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        login_user(user, remember=form.remember_me.data)
        return fl.redirect('/')
    return fl.render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.user.LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return fl.redirect("/")
        return fl.render_template('login.html',
                                  message="Неправильный логин или пароль",
                                  form=form)
    return fl.render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return fl.redirect("/")


def main():
    db_session.global_init("db/table.db", debug=False)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        db_sess = db_session.create_session()
        return db_sess.get(User, user_id)

    app.run()


if __name__ == '__main__':
    main()
