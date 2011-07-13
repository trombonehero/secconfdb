import datetime
import db

import flask

app = flask.Flask(__name__)


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

def tags(request):
	if request.cookies.has_key('tags'):
		cookie = request.cookies['tags']
		if len(cookie) == 0: return []
		return sorted(cookie.split(','))

	return [ 'security', 'privacy', 'crypto' ]


@app.route('/')
def hello():
	tag_names = tags(flask.request)
	current_tags = [ id for (id, name) in db.get_tags(tag_names) ]
	if len(tag_names) == 0: tag_names = None

	return flask.render_template('main.html',
			tags = tag_names,
			year = 2011,
			deadlines = db.deadlines(current_tags),
			upcoming = db.upcoming(current_tags),
			recent = db.recent(current_tags),
			soonness = soonness)

@app.route('/preferences')
def prefs():
	return flask.render_template('prefs.html',
			all_tags = db.get_tags(),
			current_tags = tags(flask.request)
		)

@app.route('/setprefs', methods = [ 'POST' ])
def setprefs():

	current_tags = []

	for key in flask.request.form:
		if key.startswith('tag:'):
			current_tags.append(key[4:])

	response = app.make_response(flask.redirect('/'))
	response.set_cookie('tags',
			max_age = 10 * 365 * 24 * 3600,
			value = ','.join(sorted(current_tags)))

	return response


def make_calendar(events, title):
	return flask.Response(
		response = flask.render_template('vcal',
			events = events, title = title, datetime = datetime),
		mimetype = 'text/plain')

@app.route('/conferences.ics')
def conference_calendar():
	events = [
		(
			event.abbreviation, event.name, event.where(),
			(event.startDate, event.endDate)
		)
		for event in db.upcoming()
	]

	return make_calendar(events, 'Upcoming Conferences')

@app.route('/deadlines.ics')
def deadline_calendar():
	events = []
	for conf in db.deadlines():
		if conf.extendedDeadline:
			events.append(
				(
					"%s Deadline (extended)" % conf.abbreviation,
					"Extended paper deadline for %s" % conf.name,
					conf.where(),
					conf.extendedDeadline,
				))
		elif conf.deadline:
			events.append(
				(
					"%s Deadline" % conf.abbreviation,
					"Paper deadline for %s" % conf.name,
					conf.where(),
					conf.deadline,
				))

		if conf.posterDeadline:
			events.append(
				(
					"%s Poster Deadline" % conf.abbreviation,
					"Poster deadline for %s" % conf.name,
					conf.where(),
					conf.posterDeadline,
				))

	return make_calendar(events, 'Conference Deadlines')


# Conference info, either by ID or by abbreviation.
@app.route('/conference/<int:conf_id>')
def conference_by_id(conf_id):
	(conference, events) = db.conference_events(id = conf_id)
	if len(events) == 0: flask.abort(404)

	return flask.render_template('conference.html',
		conference = conference,
		events = events)

@app.route('/conference/<string:abbreviation>')
def conference_by_name(abbreviation):
	(conference, events) = db.conference_events(abbreviation = abbreviation)
	if len(events) == 0: flask.abort(404)

	return flask.render_template('conference.html',
		conference = conference,
		events = events)

if __name__ == '__main__':
	app.run(debug = True)

