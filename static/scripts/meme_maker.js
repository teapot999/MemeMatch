function previewMeme(input) {
    if (input.files && input.files[0]) {
        document.getElementById('text-toggler').disabled = false;
        document.getElementById('jackal-toggler').disabled = false;
        document.getElementById('demik-toggler').disabled = false;

        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('meme-source').src = e.target.result;
            document.getElementById('meme-preview').src = e.target.result;
        };
        reader.readAsDataURL(input.files[0]);
    }
}


/**
 * @param {HTMLImageElement} image - Исходная пикча
 * @param canvas - Исходный canvas
 * @param ctx - Исходный ctx
 * @param options - Параметры мема:
 * @param {string} options.topText - Текст сверху
 * @param {string} options.bottomText - Текст снизу
 * @returns {Promise<void>}
 */
async function makeTextMeme(image, canvas, ctx, options) {
    let {
        topText = '', bottomText = ''
    } = options;

    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    ctx.drawImage(image, 0, 0);

    const drawText = (text, y, isTop) => {
        const fontSize = canvas.width / 10;
        ctx.font = `bold ${fontSize}px Impact`;
        ctx.fillStyle = 'white';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = fontSize / 30;
        ctx.textAlign = 'center';
        ctx.textBaseline = isTop ? 'top' : 'bottom';

        ctx.fillText(text.trim().toUpperCase(), canvas.width / 2, y);
        ctx.strokeText(text.trim().toUpperCase(), canvas.width / 2, y);
    };

    if (topText) drawText(topText, 10, true);
    if (bottomText) drawText(bottomText, canvas.height - 10, false);
}

/**
 * @param image - Исходная пикча
 * @param options - Параметры мема:
 * @param {number} options.jackalDegree - Степень шакализации
 * @param {number} options.jackalPower - Количество итераций
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
    let {
        demikTopText = '', demikBottomText = '', demikBorder = 100, demikOutline = 3
    } = options;

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
    ctx.font = `${demikBorder * 1.5}px "Consolas"`;
    ctx.fillText(demikTopText, canvas.width / 2, image.naturalHeight + demikBorder * 4);
    ctx.font = `${demikBorder * 0.8}px "Consolas"`;
    ctx.fillText(demikBottomText, canvas.width / 2, image.naturalHeight + demikBorder * 5.2);
}

async function makeMeme(imageSource, imagePreview, options) {
    const canvas = document.createElement('canvas');
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

    let currentSource = imageSource;

    if (jackalType) {
        let params = { jackalDegree };
        const jackalBase64 = await makeJackalMeme(currentSource, params);
        currentSource = await new Promise(res => {
            const img = new Image();
            img.onload = () => res(img);
            img.src = jackalBase64;
        });
    }

    if (textType) {
        let params = { topText, bottomText }
        await makeTextMeme(currentSource, canvas, ctx, params);
        currentSource = await new Promise(res => {
            const img = new Image();
            img.onload = () => res(img);
            img.src = canvas.toDataURL();
        });
    }

    if (demikType) {
        let params = { demikTopText, demikBottomText, demikBorder, demikOutline }
        await makeDemikMeme(currentSource, canvas, ctx, params);
    }

    // console.log("Options:", options);
    // console.log("Canvas size:", canvas.width, "x", canvas.height);
    imagePreview.src = canvas.toDataURL('image/jpeg', 0.9);
}