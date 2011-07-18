import flask
import functools

import db


def authenticate():
	return flask.Response('Login required', 401,
			{'WWW-Authenticate': 'Basic realm="SECCONFDB"'})


credentials = {
	'database': 'secconfdb',
	'username': 'secconfdb',
	'password': '',
}


def requires_auth(f):
	""" Decorator which says "we need real credentials for this operation". """
	@functools.wraps(f)
	def decorated(*args, **kwargs):
		global credentials

		auth = flask.request.authorization
		if not auth: return authenticate()

		credentials.update(auth)

		try: db.connect(**credentials)
		except db.UnauthorizedAccessException: return authenticate()

		return f(*args, **kwargs)
	return decorated

