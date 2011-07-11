import db

import flask
import jinja2

app = flask.Flask(__name__)

jinja = jinja2.Environment(loader = jinja2.PackageLoader('secconfdb', 'layout'))

row = jinja2.Template("""
<tr>
	<td>{{ conf.abbreviation }}</td>
	<td>{{ conf.when() }}</td>
	<td>{{ conf.where() }}</td>
</tr>
""")

@app.route("/")
def hello():
	template = jinja.get_template("main.html")
	return template.render(conferences = db.defaultQuery(), year = 2011)


if __name__ == "__main__":
	for conf in db.defaultQuery():
		print repr(conf)
	app.run(debug = True)

