import os
from functools import wraps

from dotenv import load_dotenv
from flask import abort
from flask_login import current_user

from data import db_session

load_dotenv()


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
