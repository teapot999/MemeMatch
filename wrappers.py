import os
from functools import wraps

from dotenv import load_dotenv
from flask import abort, request, jsonify, g
from flask_login import current_user
from redis import Redis

from data import db_session
from data.users import User

load_dotenv()

rediska = Redis(host=os.getenv('HOST', 'localhost'), port=6379, db=0)

MAX_REQUESTS = 5
TIME_WINDOW = 10


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or str(current_user.id) != os.getenv('ADMIN_ID'):
            return abort(418)
        return func(*args, **kwargs)

    return wrapper


def current_user_only(model, url_param='id'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            item_id = kwargs.get(url_param)
            if item_id is None:
                return abort(404)

            with (db_session.create_session() as db_sess):
                item = db_sess.get(model, item_id)
                if item is None:
                    return abort(404)

                owner_id = item.id if hasattr(item, 'hashed_password') else \
                    getattr(item, 'user_id', getattr(item, 'author_id', None))

                if not current_user.is_authenticated or current_user.id != owner_id:
                    return abort(403)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def is_rate_limited_redis(user_id):
    key = f'rate:user:{user_id}'

    current_requests = rediska.incr(key)
    if current_requests == 1:
        rediska.expire(key, TIME_WINDOW)

    if current_requests > MAX_REQUESTS:
        return True
    return False


def api_or_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            g.api_user = current_user
            return func(*args, **kwargs)

        api_key = request.headers.get('X-API-Key')
        if api_key:
            with db_session.create_session() as db_sess:
                user = db_sess.query(User).filter(User.api_key == api_key).first()
                if user:
                    if is_rate_limited_redis(user.id):
                        return jsonify({
                            'status': 'error',
                            'message': f'Too many requests. Limit is {MAX_REQUESTS} requests per {TIME_WINDOW} seconds.'
                        }), 429

                    g.api_user = user
                    return func(*args, **kwargs)

        return jsonify({
            'status': 'error',
            'message': 'Unauthorized. Provide a valid X-API-Key header or log in.'
        }), 401

    return wrapper
