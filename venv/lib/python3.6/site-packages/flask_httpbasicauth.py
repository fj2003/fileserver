"""
flask_httpauth
==================

This module provides Basic authentication for Flask routes.

:copyright: (C) 2018 by Viktor Hansson
:license:   BSD, see LICENSE.txt for more details.
"""

from functools import wraps
from flask import request, make_response, session


class HTTPAuth(object):
    def __init__(self):
        def default_get_user(username):
            return None

        def default_auth_error():
            return "Unauthorized Access"

        self.realm = "Authentication Required"
        self.get_user(default_get_user)
        self.error_handler(default_auth_error)

    def get_user(self, f):
        self.get_user_callback = f
        return f

    def error_handler(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            res = f(*args, **kwargs)
            if type(res) == str:
                res = make_response(res)
                res.status_code = 401
            if 'WWW-Authenticate' not in res.headers.keys():
                res.headers['WWW-Authenticate'] = self.authenticate_header()
            return res
        self.auth_error_callback = decorated
        return decorated


    def login_required(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            # We need to ignore authentication headers for OPTIONS to avoid
            # unwanted interactions with CORS.
            # Chrome and Firefox issue a preflight OPTIONS request to check
            # Access-Control-* headers, and will fail if it returns 401.
            if request.method != 'OPTIONS':
                if auth:
                    user = self.get_user_callback(request, auth.username)
                else:
                    return self.auth_error_callback()
                if user is None or not self.authenticate(auth, user['password']):
                    return self.auth_error_callback()
                request.user = user
            return f(*args, **kwargs)
        return decorated


class HTTPBasicAuth(HTTPAuth):
    def __init__(self):
        super(HTTPBasicAuth, self).__init__()
        self.hash_password_callback = None
        self.verify_password_callback = None

    def hash_password(self, f):
        self.hash_password_callback = f
        return f

    def verify_password(self, f):
        """
        The verify_password callback takes 2 parameters: stored_password and provided_password.
        """
        self.verify_password_callback = f
        return f

    def authenticate_header(self):
        return 'Basic realm="{0}"'.format(self.realm)

    def authenticate(self, auth, stored_password):
        if not auth:
            return False

        if self.verify_password_callback:
            return self.verify_password_callback(stored_password, auth.password)
        if self.hash_password_callback:
            try:
                provided_password = self.hash_password_callback(auth.password)
            except TypeError:
                provided_password = self.hash_password_callback(auth.username,
                                                                auth.password)
            return provided_password == stored_password
        return False


