import datetime
import flask


def soonness(date):
	""" Translate a deadline into a CSS class like 'reallySoon'. """
	if date is None: return "dateUnspecified"

	days_left = (date - datetime.date.today()).days
	for (days, category) in (
			(0, 'tooLate'),
			(7, 'reallySoon'),
			(28, 'soon'),
			(90, 'notSoon')):
		if days_left < days: return category

	return ""

def tags():
	""" The names of the tags currently being used to filter conferences. """
	if flask.request.cookies.has_key('tags'):
		cookie = flask.request.cookies['tags']
		if len(cookie) == 0: return []
		return sorted(cookie.split(','))

	return [ 'security', 'privacy', 'crypto' ]


def one_day():
	return datetime.timedelta(1)


def make_vcal(events, title):
	""" Create a vCal file from a list of events. """
	return flask.Response(
		response = flask.render_template('vcal',
			events = events, title = title, datetime = datetime),
		mimetype = 'text/plain')

