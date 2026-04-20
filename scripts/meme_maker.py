from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def jackal_photo(media_content, degree):
    img = Image.open(BytesIO(media_content))
    img = img.convert('RGB')
    wid, hei = img.size

    meme = img.copy().reduce(int(degree)).resize((wid, hei)).convert('RGB')

    return meme


def demik_photo(media_content, indent, frame_width, top_text, bottom_text):
    indent_to_img = 20
    font = ImageFont.truetype('consola.ttf')

    img = Image.open(BytesIO(media_content))
    img = img.convert('RGB')
    wid, hei = img.size

    meme = Image.new(
        'RGB', (wid + (indent + indent_to_img) * 2, hei + (indent + indent_to_img) * 2 + 130), (0, 0, 0))
    draw = ImageDraw.Draw(meme)
    draw.rectangle((indent, indent, wid + indent + indent_to_img * 2, hei + indent + indent_to_img * 2), width=frame_width)
    meme.paste(img, (indent + indent_to_img, indent + indent_to_img))

    top_text_font = ImageFont.truetype('consola.ttf', size=(wid / (50 * 0.55) * 2))
    top_text_length = draw.textlength(top_text, font=font) * 5.2
    draw.text(
        xy=(wid / 2 + (indent + indent_to_img) - top_text_length,
            hei + indent + indent // 3 + 30),
        text=top_text, font=top_text_font, align='center')

    bottom_text_font = ImageFont.truetype('consola.ttf', size=(hei / (70 * 0.55) * 2))
    bottom_text_length = draw.textlength(bottom_text, font=font) * 3.68
    draw.text(
        xy=(wid / 2 + (indent + indent_to_img) - bottom_text_length,
            hei + indent + indent // 3 + 130),
        text=bottom_text, font=bottom_text_font, align='center')

    return meme


im = open('../fullbody.png', 'rb').read()

# demik_image = demik_photo(im, 80, 3, '1234567' * 4, '1234567890120' * 3)  # 28; 39
# demik_image.show()
jackal_image = jackal_photo(im, 50)
jackal_image.quantize(52).convert('RGB').save('jackal.jpg', 'JPEG', quality=0)  # Создадим картинку и тут же ее покажем встроенным просмотрщиком операционной системы
j = Image.open('jackal.jpg')
# jackal_image.show()
j.show()
