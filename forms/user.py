from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField, FileField
from wtforms.validators import DataRequired, ValidationError, Length, Regexp, EqualTo


class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=5, max=32),
        Regexp('^[A-Za-z0-9][A-Za-z0-9_~]*[A-Za-z0-9]$')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[
        DataRequired(),
        EqualTo('password')])
    nickname = StringField('Никнейм', validators=[
        DataRequired(message='Имени не может не быть')])
    about = TextAreaField('Немного о себе')
    picture = FileField('Загрузить пикчу', validators=[
        FileAllowed(['png', 'jpg', 'jpeg'], message='Не вижу картинки с форматом JPEG, JPG или PNG')
    ])
    remember_me = BooleanField('Выпить таблетку от деменции')
    submit = SubmitField('Зарегистрироваться')

    def validate_picture(self, field):
        if field.data:
            max_size = 1.6 * 1024 * 1024
            if len(field.data.read()) > max_size:
                raise ValidationError('Пикча слишком тяжёлая, у компьютера памяти всего 1.6 мегабайт')

            field.data.seek(0)


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Выпить таблетку от деменции')
    submit = SubmitField('Войти')


class EditProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        Length(max=32),
        Regexp('^[A-Za-z0-9][A-Za-z0-9_~]*[A-Za-z0-9]$|$')
    ])
    password = PasswordField('Пароль')
    password_again = PasswordField('Повторите пароль', validators=[
        EqualTo('password')])
    nickname = StringField('Никнейм')
    about = TextAreaField('Немного о себе')
    picture = FileField('Загрузить пикчу', validators=[
        FileAllowed(['png', 'jpg', 'jpeg'], message='Не вижу картинки с форматом JPEG, JPG или PNG')
    ])
    submit = SubmitField('Подтвердить')
