from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField, FileField
from wtforms.validators import DataRequired, ValidationError


class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    nickname = StringField('Никнейм', validators=[DataRequired()])
    about = TextAreaField('Немного о себе')
    picture = FileField('Загрузить пикчу', validators=[FileAllowed(['png', 'jpg', 'jpeg'])])
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
