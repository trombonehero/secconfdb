import flask
import functools

import db


def authenticate(message = 'Login required'):
	return flask.Response(message, 401,
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

		try: db.cursor(**credentials)
		except db.UnauthorizedAccessException, message:
			return authenticate(message)

		return f(*args, **kwargs)
	return decorated

