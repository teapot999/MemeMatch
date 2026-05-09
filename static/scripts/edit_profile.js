function previewNickname(input) {
    const nickname = document.getElementById("preview-nickname");
    if (input.value.trim()) {
        nickname.textContent = input.value;
    } else {
        nickname.textContent = "{{ current_user.nickname }}"
    }
}

function previewAbout(input) {
    const about = document.getElementById('preview-about');
    if (input.value.trim()) {
        about.textContent = input.value;
    } else {
        about.textContent = "{{ current_user.about }}"
    }
}

function previewImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('preview-image').src = e.target.result;
        };
        reader.readAsDataURL(input.files[0]);
    }
}