from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import StringField, SubmitField, BooleanField, FileField, IntegerRangeField
from wtforms.validators import DataRequired, ValidationError, NumberRange


class MakingForm(FlaskForm):
    picture = FileField('Загрузить будущий шедевр', render_kw={'accept': 'image/*'}, validators=[
        DataRequired(),
        FileAllowed(['png', 'jpg', 'jpeg'], message='Не вижу картинки с форматом JPEG, JPG или PNG')
    ])

    text = BooleanField('Мемно подписать', default=False)
    text_top = StringField('Надпись сверху')
    text_bottom = StringField('Надпись снизу')

    jackal = BooleanField('Зашакалить', default=False)
    jackal_degree = IntegerRangeField('Степень шакальности', default=15, validators=[
        NumberRange(0, 25)
    ])

    demik = BooleanField('Сделать демик', default=False)
    demik_top_text = StringField('Надпись сверху')
    demik_bottom_text = StringField('Надпись снизу')
    demik_frame_width = IntegerRangeField('Ширина рамки', default=52, validators=[
        NumberRange(20, 100)
    ])
    demik_outline_width = IntegerRangeField('Толщина обводки картинки', default=3, validators=[
        NumberRange(1, 10)
    ])

    create = SubmitField('Создать мем')

    def validate_picture(self, field):
        if field.data:
            max_size = 3.2 * 1024 * 1024
            if len(field.data.read()) > max_size:
                raise ValidationError('Пикча слишком тяжёлая, у компьютера памяти всего 3.2 мегабайта')

            field.data.seek(0)


class UploadingForm(FlaskForm):
    title = StringField('Заголовок поста', validators=[DataRequired()])
    descr = StringField('Описание поста')
    upload = SubmitField('Выложить мем')
