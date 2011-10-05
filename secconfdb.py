#!/usr/bin/python

import db
import flask
import re

import auth
import utils

app = flask.Flask(__name__)


@app.route('/')
def main():
	""" Main "entry point" for the site. """

	# What tags are we using to filter results?
	tag_names = utils.tags()
	current_tags = [ id for (id, name) in db.get_tags(tag_names) ]
	if len(tag_names) == 0: tag_names = None

	# Render from the 'main' template.
	return flask.render_template('main.html',
			tags = tag_names,
			year = 2011,
			deadlines = db.deadlines(current_tags),
			upcoming = db.upcoming(current_tags),
			recent = db.recent(current_tags),
			utils = utils)


@app.route('/conference/<string:abbreviation>')
def conference(abbreviation):
	""" Render information about a particular conference (e.g. all events). """
	(conference, events) = db.conference_events(abbreviation = abbreviation)
	if len(events) == 0: flask.abort(404)

	return flask.render_template('conference.html',
		conference = conference,
		events = events)


# User preferences.
@app.route('/preferences')
def prefs():
	""" Ask the user for preferences. """
	return flask.render_template('prefs.html',
			all_tags = db.get_tags(),
			current_tags = utils.tags()
		)

@app.route('/setprefs', methods = [ 'POST' ])
def setprefs():
	""" Save user preferences in a cookie. """
	current_tags = []
	for key in flask.request.form:
		if key.startswith('tag:'):
			current_tags.append(key[4:])

	response = app.make_response(flask.redirect('/'))
	response.set_cookie('tags',
			max_age = 10 * 365 * 24 * 3600,
			value = ','.join(sorted(current_tags)))

	return response


@app.route('/most_recent')
def most_recent():
	""" What conferences do we need to update? """
	return flask.render_template('most_recent.html',
			year = 2011,
			conferences = db.most_recent(),
			utils = utils)


# vCal files for upcoming conferences and deadlines.
@app.route('/conferences.ics')
def conference_calendar():
	""" A vCal file of upcoming conferences. """
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
	""" A vCal file of impending deadlines. """
	events = []
	for conf in db.deadlines():
		# Use extended paper deadline if it exists, or the original otherwise.
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

		# A conference may also have a poster deadline.
		if conf.posterDeadline:
			events.append(
				(
					"%s Poster Deadline" % conf.abbreviation,
					"Poster deadline for %s" % conf.name,
					conf.where(),
					conf.posterDeadline,
				))

	return utils.make_vcal(events, 'Conference Deadlines')



# Code for editing conferences and their events.
@app.route('/edit/conference/<string:abbreviation>')
def edit_conference(abbreviation):
	""" Edit a particular conference (e.g. all events). """
	(conference, events) = db.conference_events(abbreviation = abbreviation)

	conferences = [
		(c.conference, '%s: %s' % (c.abbreviation, c.name))
			for c in db.conferences() ]

	locations = [
		(l.location_id, l.where()) for l in db.locations() ]

	meeting_types = [ (m.type_id, m.name) for m in db.meeting_types() ]

	return flask.render_template('edit/conference.html',
			all_tags = [ name for (id, name) in db.get_tags() ],
			conferences = conferences,
			conference = conference,
			events = events,
			locations = locations,
			meeting_types = meeting_types,
		)



valid_date = re.compile('[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$')
def date(s):
	if valid_date.match(s): return s
	else: raise ValueError, "'%s' is not a valid date (YYYY-MM-DD)" % s

valid_url = re.compile('https?://[A-Za-z0-9\-\_\.\/]+$')
def url(s):
	if valid_url.match(s): return s
	else: raise ValueError, "'%s' is not a valid URL" % s

valid_abbrev = re.compile('[A-Za-z0-9\-]+$')
def abbrev(s):
	if valid_abbrev.match(s): return s
	else: raise ValueError, "'%s' is not a valid conference abbreviation" % s

valid_text = re.compile('[A-Za-z0-9, \-\_\.\(\)]*$')
def text(s):
	if valid_text.match(s): return s
	else: raise ValueError, "'%s' is not database-safe text" % s

valid_tags = re.compile('[a-z ,]+$')
def tags(s):
	if valid_tags.match(s):
		names = s.split(',')
		values = [ str(i) for (i,name) in db.get_tags(names) ]
		return ','.join(values)
	else: raise ValueError, "'%s' is not database-safe text" % s


@app.route('/edit/conference/create_event', methods = [ 'POST' ])
@auth.requires_auth
def create_event():
	new_value = {}
	posted = flask.request.form
	print posted

	# POST form -> SQL mapping
	fields = {
		'start':     (date, 'startDate'),
		'end':       (date, 'endDate'),
		'deadline':  (date, 'deadline'),
		'extended':  (date, 'extendedDeadline'),
		'poster':    (date, 'posterDeadline'),
		'url':       (url,  'url'),
		'proc':      (url,  'proceedings'),
		'conference':(int,  'conference'),
		'location':  (int,  'location'),
	}

	try:
		for (name, (type_converter, field_name)) in fields.items():
			if not name in posted or len(posted[name]) == 0:
				new_value[field_name] = None
				continue

			new_value[field_name] = str(type_converter(posted[name]))

	except ValueError, e:
		flask.abort(400, e)

	try:
		db.create('ConferenceInstances', values = new_value,
				credentials = auth.credentials)

	except db.UnauthorizedAccessException, message:
		return auth.authenticate(message)

	return flask.redirect('/edit/conference/%s' % posted['abbreviation'])


@app.route('/edit/conference/update_event', methods = [ 'POST' ])
@auth.requires_auth
def update_event():
	new_value = {}
	posted = flask.request.form

	# POST form -> SQL mapping
	fields = {
		'start':     (date, 'startDate'),
		'end':       (date, 'endDate'),
		'deadline':  (date, 'deadline'),
		'extended':  (date, 'extendedDeadline'),
		'poster':    (date, 'posterDeadline'),
		'url':       (url,  'url'),
		'proc':      (url,  'proceedings'),
		'location':  (int,  'location'),
	}

	try:
		for (name, (type_converter, field_name)) in fields.items():
			if not name in posted or len(posted[name]) == 0:
				new_value[field_name] = None
				continue

			new_value[field_name] = type_converter(posted[name])

	except ValueError, e:
		flask.abort(400, e)

	try:
		db.update('ConferenceInstances', key = ('instance', int(posted['id'])),
				values = new_value, credentials = auth.credentials)

	except db.UnauthorizedAccessException, message:
		return auth.authenticate(message)

	return flask.redirect('/edit/conference/%s' % abbrev(posted['conference']))


@app.route('/edit/conference/update_conference', methods = [ 'POST' ])
@auth.requires_auth
def update_conference():
	new_value = {}
	posted = flask.request.form

	# POST form -> SQL mapping
	fields = {
		'name':      (str,    'name'),
		'abbrev':    (abbrev, 'abbreviation'),
		'type':      (int,    '`meeting-type`'),
		'parent':    (int,    'parent'),
		'url':       (url,    'permanentURL'),
		'desc':      (str,    'description'),
		'tags':      (tags,   'tags'),
	}
	conference_id = int(posted['id'])

	try:
		for (name, (type_converter, field_name)) in fields.items():
			if not name in posted or len(posted[name]) == 0:
				new_value[field_name] = None
				continue

			new_value[field_name] = type_converter(posted[name])

	except ValueError, e:
		flask.abort(400, e)

	try:
		db.update('Conferences', key = ('conference', conference_id),
				values = new_value, credentials = auth.credentials)

	except db.UnauthorizedAccessException, message:
		return auth.authenticate(message)

	abbrev_noquotes = new_value['abbreviation'][1:-1]
	return flask.redirect('/edit/conference/%s' % abbrev_noquotes)


# Code to edit very simple tables (id -> text)
@app.route('/edit/simple/<string:table_name>')
def edit_simple(table_name):
	values = db.get(table_name)

	headers = []
	if len(values) > 0: headers = values[0].__dict__.keys()

	return flask.render_template('edit/simple.html',
			table = table_name,
			headers = headers,
			values = values,
		)


@app.route('/edit/update', methods = [ 'post' ])
@auth.requires_auth
def update_simple():
	posted = flask.request.form

	table_name = abbrev(posted['table name'])
	key_field = abbrev(posted['table key'])

	new_value = {}
	for key in posted.keys():
		if key.startswith('table '): continue
		if key == key_field: continue

		new_value[key] = text(posted[key])

	try:
		db.update(table_name,
				key = (key_field, int(posted[key_field])),
				values = new_value, credentials = auth.credentials)

	except db.UnauthorizedAccessException, message:
		return auth.authenticate(message)

	return flask.redirect('/edit/simple/%s' % table_name)


@app.route('/edit/create', methods = [ 'post' ])
@auth.requires_auth
def create_simple():
	posted = flask.request.form
	table_name = abbrev(posted['table name'])

	new_value = {}
	for key in posted.keys():
		if key.startswith('table '): continue

		value = posted[key]
		if value.startswith('http'): value = url(value)
		else: value = text(posted[key])

		if value == '': continue

		if '-' in key: key = '`%s`' % key
		new_value[key] = value

	try:
		db.create(table_name, values = new_value, credentials = auth.credentials)

	except db.UnauthorizedAccessException, message:
		return auth.authenticate(message)

	return flask.redirect('/edit/simple/%s' % table_name)


# Code to edit conferences
@app.route('/edit/conferences')
def edit_conferences():
	conferences = db.conferences()
	parents = [ (None, '') ] + [
		(c.conference, '%s: %s' % (c.abbreviation, c.name)) for c in conferences
	]

	tags = dict(db.get_tags())

	return flask.render_template('edit/conferences.html',
			table = 'Conferences',
			tags = tags,
			conferences = conferences,
			parents = parents,
			prototype = event.Event,
		)

@app.route('/edit/create_conference', methods = [ 'post' ])
@auth.requires_auth
def create_conference():
	posted = flask.request.form
	new_value = {}

	# POST form -> SQL mapping
	fields = {
		'name':      (text, 'name'),
		'abbrev':    (text, 'abbreviation'),
		'desc':      (text, 'description'),
		'tags':      (tags, 'tags'),
		'parent':    (int,  'parent'),
		'url':       (url,  'url'),
	}

	try:
		for (name, (type_converter, field_name)) in fields.items():
			if not name in posted or len(posted[name]) == 0:
				new_value[field_name] = None
				continue

			new_value[field_name] = type_converter(posted[name])

	except ValueError, e:
		flask.abort(400, e)

	return str('<br/>'.join([ '%s: %s' % i for i in posted.items() ]))


if __name__ == '__main__':
	app.run(debug = True)

