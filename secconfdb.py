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
	return template.render(conferences = db.defaultQuery(),
			year = 2011, soonness = soonness)


@app.route('/calendar.ics')
def calendar():
	template = jinja.get_template('vcal')
	return template.render(events = db.defaultQuery(), datetime = datetime)


# Conference info, either by ID or by abbreviation.
@app.route('/conference/<int:conf_id>')
def confernece(conf_id):
	return "Let's look up conference %d" % conf_id

@app.route('/conference/<string:abbreviation>')
def conference(abbreviation):
	return "Let's look up conference '%s'" % abbreviation

if __name__ == '__main__':
	app.run(debug = True)

