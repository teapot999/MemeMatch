const TEXT_INDENT_FROM_END_BORDERS = 10;
const TEXT_INDENT_FROM_SIDE_BORDERS = 40;
const FONT_PRECENT_SIZE_FROM_PICTURE = 0.03;

/**
 * Хэндлер захвата новой картинки.
 * @param input - Поле для выбора файла
 */
function previewMeme(input) {
    const file = input.files[0];
    if (file) {
        if (file.type.startsWith('image/')) {
            document.getElementById('text-toggler').disabled = false;
            document.getElementById('jackal-toggler').disabled = false;
            document.getElementById('demik-toggler').disabled = false;

            const reader = new FileReader();
            reader.onload = function (e) {
                document.getElementById('meme-source').src = e.target.result;
                document.getElementById('meme-preview').src = e.target.result;
            };
            reader.readAsDataURL(input.files[0]);
        } else {
            document.getElementById('text-toggler').disabled = true;
            document.getElementById('jackal-toggler').disabled = true;
            document.getElementById('demik-toggler').disabled = true;
        }
    }
}

/**
 * Получение размера шрифта для заданной строки.
 * @param ctx
 * @param {string} text - Исходный текст
 * @param {number} imageWidth - Ширина картинки
 * @param {string} fontName - Имя шрифта
 * @param {string} additions - Настройки шрифта (формат: "bold italic")
 * @return {number}
 */
function getFontSize(ctx, text, imageWidth, fontName, additions = "") {
    let fontSize = imageWidth / 10;

    if (!text) return fontSize;

    do {
        ctx.font = `${additions} ${fontSize}px "${fontName}"`;
        const metrics = ctx.measureText(text.trim().toUpperCase());

        if (metrics.width < imageWidth - TEXT_INDENT_FROM_SIDE_BORDERS) {
            break;
        }

        fontSize -= 1;
    } while (fontSize > imageWidth * FONT_PRECENT_SIZE_FROM_PICTURE);

    return fontSize;
}

/**
 * Обрезка исходной строки до максимальной длины.
 * @param ctx - Исходный ctx
 * @param text - Исходный текст
 * @param {number} imageWidth - Ширина картинки
 * @param {number} definedFontSize - Размер шрифта
 * @return {string}
 */
function fitText(ctx, text, imageWidth, definedFontSize = 0) {
    let measuredText = text;
    let fontSize = definedFontSize > 0 ? definedFontSize : getFontSize(ctx, text, imageWidth, 'Times New Roman');
    ctx.font = `${fontSize}px "Times New Roman"`

    while (ctx.measureText(measuredText).width > imageWidth && measuredText.length > 0) {
        measuredText = measuredText.slice(0, -1);
    }
    return measuredText;
}

/**
 * Создание текстового мема (подписи сверху и снизу).
 * @param {HTMLImageElement} image - Исходная пикча
 * @param canvas - Исходный canvas
 * @param ctx - Исходный ctx
 * @param options - Параметры мема:
 * @param {string} options.topText - Текст сверху
 * @param {string} options.bottomText - Текст снизу
 * @returns {Promise<void>}
 */
async function makeTextMeme(image, canvas, ctx, options) {
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;

    ctx.drawImage(image, 0, 0);

    let {
        topText = '', bottomText = ''
    } = options;

    const drawText = async (text, y, isTop) => {
        const fontSize = getFontSize(ctx, text, canvas.width, 'Impact', 'bold');
        ctx.font = `bold ${fontSize}px Impact`;

        const maxWidth = canvas.width - TEXT_INDENT_FROM_SIDE_BORDERS;

        let resultText = text.trim().toUpperCase();
        while (ctx.measureText(resultText).width > maxWidth && resultText.length > 0) {
            resultText = resultText.slice(0, -1);
        }

        ctx.fillStyle = 'white';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = fontSize / 30;
        ctx.textAlign = 'center';
        ctx.textBaseline = isTop ? 'top' : 'bottom';

        ctx.fillText(resultText, canvas.width / 2, y);
        ctx.strokeText(resultText, canvas.width / 2, y);

        if (resultText.length < text.trim().toUpperCase().length) {
            const inputId = isTop ? 'topText' : 'bottomText';
            const input = document.getElementById(inputId);
            const start = input.selectionStart;
            const end = input.selectionEnd;

            input.value = input.value.slice(0, resultText.length);
            input.setSelectionRange(start, end);
        }
    };

    if (topText) await drawText(topText, TEXT_INDENT_FROM_END_BORDERS, true);
    if (bottomText) await drawText(bottomText, canvas.height - TEXT_INDENT_FROM_END_BORDERS, false);
}

/**
 * Создание шакального мема (изображение с потерей в качестве).
 * @param image - Исходная пикча
 * @param options - Параметры мема:
 * @param {number} options.jackalDegree - Степень шакализации
 */
async function makeJackalMeme(image, options) {
    let {jackalDegree = 0} = options;

    const quality = Math.max(0.01, 0.25 - jackalDegree / 25);
    const scale = Math.max(0.02, 1 - (jackalDegree / 25)); // Ещё сильнее уменьшаем

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    ctx.imageSmoothingEnabled = false;

    const sw = canvas.width * scale;
    const sh = canvas.height * scale;
    ctx.drawImage(image, 0, 0, sw, sh);

    ctx.drawImage(canvas, 0, 0, sw, sh, 0, 0, canvas.width, canvas.height);

    return canvas.toDataURL('image/jpeg', quality);
}


/**
 * Создание мема-демотиватора (чёрная рамка и подпись снизу).
 * @param {HTMLImageElement} image - Исходная пикча
 * @param canvas - Исходный canvas
 * @param ctx - Исходный ctx
 * @param options - Параметры мема:
 * @param {string} options.demikTopText - Текст сверху
 * @param {string} options.demikBottomText - Текст снизу
 * @param {number} options.demikBorder - Толщина чёрной рамки демотиватора
 * @param {number} options.demikOutline - Толщина белой обводки картинки в демотиваторе
 * @returns {Promise<void>}
 */
async function makeDemikMeme(image, canvas, ctx, options) {
    let {demikTopText = '', demikBottomText = '', demikBorder = 100, demikOutline = 3} = options;

    canvas.width = image.naturalWidth + demikBorder * 4;
    canvas.height = image.naturalHeight + demikBorder * 6;

    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.drawImage(image, demikBorder * 2, demikBorder * 2);

    ctx.strokeStyle = 'white';
    ctx.lineWidth = demikOutline;
    ctx.strokeRect(demikBorder * 2 - 5, demikBorder * 2 - 5, image.naturalWidth + 10, image.naturalHeight + 10);

    ctx.fillStyle = 'white';
    ctx.textAlign = 'center';

    const maxWidth = canvas.width - demikBorder - TEXT_INDENT_FROM_SIDE_BORDERS;

    const drawText = async (text, sizeCoef, bottomIndentCoef, isTop) => {
        const fontSize = demikBorder * sizeCoef;
        ctx.font = `${fontSize}px "Times New Roman"`;
        let resultText = fitText(ctx, text, maxWidth, fontSize);
        ctx.fillText(resultText, canvas.width / 2, image.naturalHeight + demikBorder * bottomIndentCoef);

        if (resultText.length < text.trim().toUpperCase().length) {
            const inputId = isTop ? 'demikTopText' : 'demikBottomText';
            const input = document.getElementById(inputId);
            const start = input.selectionStart;
            const end = input.selectionEnd;

            input.value = input.value.slice(0, resultText.length);
            input.setSelectionRange(start, end);
        }
    }

    if (demikTopText) await drawText(demikTopText, 1.2, 4, true);
    if (demikBottomText) await drawText(demikBottomText, 0.8, 5.2, false);
}

/**
 * Создание мема на основе переданных параметров, собранных по странице.
 * @param {HTMLImageElement} imageSource - Картинка-исходник
 * @param {HTMLImageElement} imagePreview - Картинка-результат
 * @param options - Параметры мема:
 * @param {boolean} options.textType - Тип мема: текстовый
 * @param {string} options.topText - Текст сверху
 * @param {string} options.bottomText - Текст снизу
 * @param {boolean} options.jackalType - Тип мема: шакальный
 * @param {number} options.jackalDegree - Степень шакализации
 * @param {boolean} options.demikType - Тип мема: демотиватор
 * @param {string} options.demikTopText - Подпись в верхней строчке
 * @param {string} options.demikBottomText - Подпись в нижней строчке
 * @param {number} options.demikBorder - Толщина чёрной рамки демотиватора
 * @param {number} options.demikOutline - Толщина белой обводки для картинки
 */
async function makeMeme(imageSource, imagePreview, options) {
    let canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    let {
        textType = false,
        topText = '',
        bottomText = '',
        jackalType = false,
        jackalDegree = 0,
        demikType = false,
        demikTopText = '',
        demikBottomText = '',
        demikBorder = 100,
        demikOutline = 3
    } = options;

    canvas.width = imageSource.naturalWidth;
    canvas.height = imageSource.naturalHeight;
    ctx.drawImage(imageSource, 0, 0);

    const sourceDataUrl = canvas.toDataURL('image/jpeg', 0.9);

    let currentSource = imageSource;

    if (jackalType) {
        let params = {jackalDegree};
        const jackalBase64 = await makeJackalMeme(currentSource, params);
        currentSource = await new Promise(res => {
            const img = new Image();
            img.onload = () => res(img);
            img.src = jackalBase64;
        });
    }

    if (textType) {
        let params = {topText, bottomText}
        await makeTextMeme(currentSource, canvas, ctx, params);
        currentSource = await new Promise(res => {
            const img = new Image();
            img.onload = () => res(img);
            img.src = canvas.toDataURL();
        });
    }

    if (demikType) {
        let params = {demikTopText, demikBottomText, demikBorder, demikOutline}
        await makeDemikMeme(currentSource, canvas, ctx, params);
    }

    if (jackalType && !textType && !demikType) {
        canvas.width = currentSource.width;
        canvas.height = currentSource.height;
        ctx.drawImage(currentSource, 0, 0);
    }

    if (canvas.width > 1280) {
        const scale = 1280 / canvas.width;
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = 1280;
        tempCanvas.height = canvas.height * scale;
        const tctx = tempCanvas.getContext('2d');

        tctx.drawImage(canvas, 0, 0, tempCanvas.width, tempCanvas.height);
        canvas = tempCanvas;
    }

    const finalDataUrl = canvas.toDataURL('image/jpeg', 0.9);
    imagePreview.src = finalDataUrl;

    const sourceInput = document.getElementById('meme-source-input');
    if (sourceInput) {
        sourceInput.value = sourceDataUrl;
    }

    const resultInput = document.getElementById('meme-result-input');
    resultInput.value = finalDataUrl;

    const metaInput = document.getElementById('meme-meta-input');
    metaInput.value = JSON.stringify(options);
}