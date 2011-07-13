import datetime
import re

import MySQLdb

from query import Query, Fields, Source, Filter, Order


def connect(db = 'secconfdb', user = 'secconfdb', passwd = None):
	connection = MySQLdb.connect(
		host = 'localhost', db = 'secconfdb', user = 'secconfdb')

	connection.cursor().execute("""
			SET NAMES utf8;
			SET CHARACTER SET utf8;
			SET character_set_connection=utf8;
		""")

	return connection


db_connection = None

def cursor():
	global db_connection
	if db_connection is None: db_connection = connect()

	try: return db_connection.cursor()
	except MySQLdb.OperationalError, (errno, message):
		# Catch dead connection, re-connect
		if errno == 2006:
			db_connection = connect()
			return db_connection.cursor()
		else: raise


def get_tags(names = None, ids = None):
	where = Filter(None)
	if names is not None:
		where = Filter("name in ('%s')" % "','".join(names))

	if ids is not None:
		where = Filter("tag in (%s)" % ','.join(ids))

	query = Query(
			fields = Fields([ 'tag', 'name' ]),
			source = Source('Tags'),
			filter = where,
			order = Order('name'))

	results = query.execute(cursor())

	return [ (i.tag, i.name) for i in results ]


def deadlines(tags = []):
	query = Query(
			filter = Filter.upcomingDeadlines() & Filter.tags(tags),
			order = Order.deadline())
	return query.execute(cursor())

def upcoming(tags = []):
	query = Query(
			filter = Filter.upcoming() & Filter.tags(tags),
			order = Order.start_date())
	return query.execute(cursor())

def recent(tags = []):
	query = Query(
			filter = Filter.recent() & Filter.tags(tags),
			order = Order.start_date(reverse = True))
	return query.execute(cursor())

def conference(id = None, abbreviation = None):
	assert (id is not None) ^ (abbreviation is not None)

	filter = None
	if id is not None: filter = Filter("conference = %d" % id)
	else: filter = Filter("abbreviation = '%s'" % abbreviation)

	c = cursor()

	conferences = Query(
			fields = Fields.conference(),
			source = Source.conference(),
			filter = filter,
			order = Order(None),
		).execute(c)

	if len(conferences) == 0: return None
	else: return conferences[0].__dict__


def conference_events(id = None, abbreviation = None):
	conf = conference(id, abbreviation)
	if conf['parent']:
		conf['parent'] = conference(id = int(conf['parent']))

	if len(conf['tags']) > 0:
		conf['tags'] = [
			name for (id, name) in get_tags(ids = conf['tags'].split(',')) ]

	events = Query(
			filter = Filter('conference = %d' % conf['conference']),
			order = Order.start_date(reverse = True),
		).execute(cursor())

	return (conf, events)


