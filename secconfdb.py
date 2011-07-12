import datetime
import db

import flask
import jinja2

app = flask.Flask(__name__)

jinja = jinja2.Environment(loader = jinja2.PackageLoader('secconfdb', 'layout'))

row = jinja2.Template('''
<tr>
	<td>{{ conf.abbreviation }}</td>
	<td>{{ conf.when() }}</td>
	<td>{{ conf.where() }}</td>
</tr>
''')


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

@app.route('/')
def hello():
	template = jinja.get_template('main.html')
	return template.render(year = 2011,
			deadlines = db.deadlines(),
			upcoming = db.upcoming(),
			recent = db.recent(),
			soonness = soonness)



def make_calendar(events, title):
	template = jinja.get_template('vcal')
	return flask.Response(
		response = template.render(
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
def confernece(conf_id):
	return "Let's look up conference %d" % conf_id

@app.route('/conference/<string:abbreviation>')
def conference(abbreviation):
	return "Let's look up conference '%s'" % abbreviation

if __name__ == '__main__':
	app.run(debug = True)

