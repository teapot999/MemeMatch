import hashlib
import os
import time
from collections import defaultdict
from functools import wraps

from dotenv import load_dotenv
from flask import abort, request, jsonify, g
from flask_login import current_user

from data import db_session
from data.users import User

load_dotenv()

API_REQUEST_HISTORY = defaultdict(list)

MAX_REQUESTS = 30
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

            with db_session.create_session() as db_sess:
                item = db_sess.get(model, item_id)
                if item is None:
                    return abort(404)

                owner_id = item.id if hasattr(item, 'hashed_password') else \
                    getattr(item, 'user_id', getattr(item, 'author_id', None))

                if not current_user.is_authenticated:
                    return abort(401)

                if current_user.id != owner_id:
                    return abort(403)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def is_rate_limited(user_id):
    now = time.time()

    API_REQUEST_HISTORY[user_id] = [t for t in API_REQUEST_HISTORY[user_id] if now - t < TIME_WINDOW]

    if len(API_REQUEST_HISTORY[user_id]) >= MAX_REQUESTS:
        return True

    API_REQUEST_HISTORY[user_id].append(now)
    return False


def api_or_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            g.api_user = current_user
            return func(*args, **kwargs)

        api_key = request.headers.get('X-Api-Key')
        if api_key:
            hashed_api_key = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
            with db_session.create_session() as db_sess:
                user = db_sess.query(User).filter(User.hashed_api_key == hashed_api_key).first()
                if user:
                    if is_rate_limited(user.id):
                        return jsonify({
                            'status': 'error',
                            'message': f'Too many requests. Limit is {MAX_REQUESTS} requests per {TIME_WINDOW} seconds.'
                        }), 429

                    g.api_user = user
                    return func(*args, **kwargs)

        return jsonify({
            'status': 'error',
            'message': 'Unauthorized. Provide a valid X-API-Key header or log in.'}), 401

    return wrapper


def api_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'status': 'error', 'message': 'Missing X-API-Key header'}), 401

        hashed_api_key = hashlib.sha256(api_key.encode('utf-8')).hexdigest()

        with db_session.create_session() as db_sess:
            user = db_sess.query(User).filter(User.hashed_api_key == hashed_api_key).first()
            if not user:
                return jsonify({'status': 'error', 'message': 'Invalid API Key'}), 401

            if is_rate_limited(user.id):
                return jsonify({'status': 'error', 'message': 'Too Many Requests'}), 429

            g.api_user = user
            return func(*args, **kwargs)

    return wrapper
