import datetime
import re

import MySQLdb

import conf

connection = MySQLdb.connect(
	host = 'localhost', db = 'secconfdb', user = 'secconfdb')

connection.cursor().execute("""
	SET NAMES utf8;
	SET CHARACTER SET utf8;
	SET character_set_connection=utf8;
""")


class Clause:
	""" A clause in a SQL query (e.g. SELECT, ORDER BY, ...). """

	def __init__(self, operator, value):
		""" 'operator' may not be None, but 'value' may. """
		assert operator != None

		self.operator = operator
		self.value = value

	def __str__(self):
		return " ".join([self.operator, self.value])

	def __add__(self, s):
		if self.value == None: return s
		else: return " ".join([self.operator, self.value, str(s)])

	def __radd__(self, s):
		if self.value == None: return s
		else: return " ".join([str(s), self.operator, self.value])


class Fields(Clause):
	def __init__(self, fields):
		assert fields != None
		assert len(fields) > 0

		self.fields = fields
		Clause.__init__(self, "SELECT", ",".join(fields))

	def names(self):
		return [ re.sub(".* AS ", "", name) for name in self.fields ]

	@classmethod
	def default(cls):
		return Fields(
			[
				"url", "conference", "abbreviation", "Conferences.name AS name",
				"startDate", "endDate",
				"deadline", "extendedDeadline", "posterDeadline",
				"Locations.name AS location",
				"Regions.name AS region",
				"Regions.code AS regionCode",
				"Countries.code AS country",
				"proceedings", "Conferences.permanentURL"
			])

class Source(Clause):
	def __init__(self, value):
		assert value != None
		Clause.__init__(self, "FROM", value)

	@classmethod
	def default(cls):
		return Source("""ConferenceInstances
        INNER JOIN Conferences USING (conference)
        INNER JOIN Locations USING (location)
        LEFT JOIN Regions USING (region)
        INNER JOIN Countries ON ((Locations.country = Countries.country)
                                OR (Regions.country = Countries.country))""")

class Filter(Clause):
	def __init__(self, value):
		Clause.__init__(self, "WHERE", value)

	@classmethod
	def recent(cls):
		return Filter("""
DATEDIFF(startDate, CURDATE()) < 0
AND DATEDIFF(startDate, CURDATE()) >= -180
""")

	@classmethod
	def upcoming(cls):
		return Filter("""
DATEDIFF(startDate, CURDATE()) >= 0
AND DATEDIFF(startDate, CURDATE()) <= 180
""")

	@classmethod
	def upcomingDeadlines(cls):
		return Filter("""
(
	(DATEDIFF(deadline, CURDATE()) >= -14)
	OR (DATEDIFF(extendedDeadline, CURDATE()) >= -14)
	OR (DATEDIFF(posterDeadline, CURDATE()) >= -14)
)""")


class Order(Clause):
	def __init__(self, value):
		Clause.__init__(self, "ORDER BY", value)

	@classmethod
	def start_date(cls, reverse = False):
		if reverse: return Order("startDate DESC")
		else: return Order("startDate")

	@classmethod
	def deadline(cls):
		return Order("""
CASE
        WHEN (DATEDIFF(deadline, CURDATE()) < -14)
              AND (extendedDeadline IS NULL
                   OR (DATEDIFF(extendedDeadline, CURDATE()) < -14))
                THEN
                        posterDeadline

        WHEN extendedDeadline IS NULL THEN deadline
        ELSE extendedDeadline
        END
""")



class Query:
	fields = Fields.default()
	source = Source.default()

	def __init__(self, filter, order):
		self.where = filter
		self.order = order

	def execute(self, cursor):
		cursor.execute(self.__str__())
		results = cursor.fetchall()

		conferences = []

		field_names = self.fields.names()
		for result in results:
			conferences.append(
				conf.ConferenceInstance(dict(zip(field_names, result))))

		return conferences

	def __str__(self):
		return self.fields + self.source + self.where + self.order



def deadlines():
	query = Query(Filter.upcomingDeadlines(), Order.deadline())
	return query.execute(connection.cursor())

def upcoming():
	query = Query(Filter.upcoming(), Order.start_date())
	return query.execute(connection.cursor())

def recent():
	query = Query(Filter.recent(), Order.start_date(reverse = True))
	return query.execute(connection.cursor())

