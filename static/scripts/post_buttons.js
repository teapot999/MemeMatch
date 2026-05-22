document.addEventListener('DOMContentLoaded', function () {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', async function (e) {
            e.preventDefault();

            const postId = this.getAttribute('data-post-id');
            const likesCountSpan = document.querySelector(`.likes-count-val-${postId}`);

            try {
                const response = await fetch(`/api/post/${postId}/like`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    }
                });
                if (!response.ok) throw new Error(`Server error: ${response.status} ${response.statusText}`);

                const data = await response.json();

                if (data.status === 'ok') {
                    if (likesCountSpan) {
                        likesCountSpan.textContent = data.likes_count;
                    }

                    const post = document.getElementById(`post-${postId}`);

                    post.classList.add('like-pulse-active');

                    setTimeout(() => {
                        post.classList.remove('like-pulse-active');
                    }, 350);

                    if (data.action === 'liked') {
                        this.classList.remove('btn-outline-danger');
                        this.classList.add('btn-danger');
                        const icon = document.getElementById(`like-icon-post-${postId}`);
                        icon.classList.remove('bi-heart-fill');
                        icon.classList.add('bi-heart');
                    } else {
                        this.classList.remove('btn-danger');
                        this.classList.add('btn-outline-danger');
                        const icon = document.getElementById(`like-icon-post-${postId}`);
                        icon.classList.remove('bi-heart');
                        icon.classList.add('bi-heart-fill');
                    }
                }
            } catch (error) {
                console.error(`Error liking post ${postId}:`, error);
            }
        });
    });
    document.querySelectorAll('.del-btn').forEach(button => {
        button.addEventListener('click', async function (e) {
            e.preventDefault();

            const postId = this.getAttribute('data-post-id');
            try {
                const postResponse = await fetch(`/api/post/${postId}`, {
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    }
                });

                if (postResponse.ok) {
                    const postData = await postResponse.json();
                    console.log(postData);

                    const matchFromPostId = postData.match_result;
                    if (matchFromPostId) {
                        const originalPostMatchesCountSpan = document.querySelector(`.matches-count-val-${matchFromPostId}`);

                        if (originalPostMatchesCountSpan) {
                            const matchesCount = Number(originalPostMatchesCountSpan.textContent);
                            originalPostMatchesCountSpan.textContent = String(matchesCount - 1);
                        }
                    }
                }

                const response = await fetch(`/api/post/${postId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    }
                });
                if (!response.ok) throw new Error(`Server error: ${response.status} ${response.statusText}`);

                const data = await response.json();
                if (data.status === 'ok') {
                    const post = document.getElementById(`post-${postId}`);
                    post.classList.add('fade-out');
                    setTimeout(() => {
                        post.remove();
                    }, 500);
                    document.getElementById(`sep-${postId}`).remove();
                }
            } catch (error) {
                console.error(`Error deleting post ${postId}:`, error);
            }
        });
    });
})