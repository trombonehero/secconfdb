import db
import flask

import utils

app = flask.Flask(__name__)


@app.route('/')
def hello():
	tag_names = utils.tags()
	current_tags = [ id for (id, name) in db.get_tags(tag_names) ]
	if len(tag_names) == 0: tag_names = None

	return flask.render_template('main.html',
			tags = tag_names,
			year = 2011,
			deadlines = db.deadlines(current_tags),
			upcoming = db.upcoming(current_tags),
			recent = db.recent(current_tags),
			utils = utils)

@app.route('/preferences')
def prefs():
	return flask.render_template('prefs.html',
			all_tags = db.get_tags(),
			current_tags = utils.tags()
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


@app.route('/conferences.ics')
def conference_calendar():
	events = [
		(
			event.abbreviation, event.name, event.where(),
			(event.startDate, event.endDate)
		)
		for event in db.upcoming()
	]

	return utils.make_vcal(events, 'Upcoming Conferences')

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

	return utils.make_vcal(events, 'Conference Deadlines')


@app.route('/conference/<string:abbreviation>')
def conference_by_name(abbreviation):
	(conference, events) = db.conference_events(abbreviation = abbreviation)
	if len(events) == 0: flask.abort(404)

	return flask.render_template('conference.html',
		conference = conference,
		events = events)

if __name__ == '__main__':
	app.run(debug = True)

