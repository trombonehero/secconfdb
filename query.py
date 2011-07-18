import re

import event


class Clause:
	""" A clause in a SQL query (e.g. SELECT, ORDER BY, ...). """

	def __init__(self, operator, value):
		""" 'operator' may not be None, but 'value' may. """
		assert operator != None

		self.operator = operator
		self.value = value

	def __str__(self):
		if self.value is None: return ""
		return " ".join([self.operator, self.value])

	def __add__(self, s):
		if self.value == None: return s
		else: return " ".join([self.operator, self.value, str(s)])

	def __radd__(self, s):
		if self.value == None: return s
		else: return " ".join([str(s), self.operator, self.value])



class Fields(Clause):
	""" Table fields that we wish to refer to (e.g. to SELECT on). """

	def __init__(self, fields):
		assert fields != None
		assert len(fields) > 0

		self.fields = fields
		Clause.__init__(self, "", ",".join(fields))

	def names(self):
		return [ re.sub(".* AS ", "", name) for name in self.fields ]

	@classmethod
	def conference(cls):
		return Fields(
			[
				'conference', 'parent', 'name', 'abbreviation', 'description',
				'permanentURL AS url', 'tags'
			])

	@classmethod
	def events(cls):
		return Fields(
			[
				"instance",
				"url", "conference", "abbreviation", "Conferences.name AS name",
				"startDate", "endDate",
				"deadline", "extendedDeadline", "posterDeadline",
				"Locations.location AS location_id",
				"Locations.name AS location",
				"Regions.name AS region",
				"Regions.code AS regionCode",
				"Countries.code AS country",
				"proceedings", "Conferences.permanentURL"
			])

	@classmethod
	def locations(cls):
		return Fields(
			[
				"Locations.location AS location_id",
				"Locations.name AS location",
				"Regions.name AS region",
				"Regions.code AS regionCode",
				"Countries.code AS country",
			])


class Values(Clause):
	""" Table values that we wish to set (e.g. foo = 42). """

	def __init__(self, values):
		assert values != None
		assert len(values) > 0

		# Put single quotes around strings, convert None to SQL-friendly NULL.
		for (name, value) in values.items():
			if value is None: values[name] = 'NULL'
			elif isinstance(value, basestring): values[name] = "'%s'" % value

		Clause.__init__(self, 'SET', ', '.join([
					'%s = %s' % (name, value) for (name, value) in values.items()
				]))


class Tables(Clause):
	""" Tables (including JOINed tables) that we can operate on. """
	def __init__(self, value, use_from = True):
		assert value != None
		Clause.__init__(self, 'FROM' if use_from else '', value)

	@classmethod
	def conference(cls):
		return Tables("Conferences")

	@classmethod
	def events(cls):
		return Tables("""ConferenceInstances
        INNER JOIN Conferences USING (conference)
        INNER JOIN Locations USING (location)
        LEFT JOIN Regions USING (region)
        INNER JOIN Countries ON ((Locations.country = Countries.country)
                                OR (Regions.country = Countries.country))""")

	@classmethod
	def locations(cls):
		return Tables("""Locations
			LEFT JOIN Regions USING (region)
			INNER JOIN Countries ON ((Locations.country = Countries.country)
                                 OR (Regions.country = Countries.country))""")


class Filter(Clause):
	""" A filter which restricts a query (e.g. WHERE foo > 42). """

	def __init__(self, value):
		Clause.__init__(self, "WHERE", value)

	def __and__(self, other):
		if self.value is None: return other
		if other.value is None: return self

		return Filter('(%s) AND (%s)' % (self.value, other.value))

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
	(DATEDIFF(deadline, CURDATE()) >= -14)
	OR (DATEDIFF(extendedDeadline, CURDATE()) >= -14)
	OR (DATEDIFF(posterDeadline, CURDATE()) >= -14)
	""")


	@classmethod
	def tags(cls, tags):
		if len(tags) == 0: return Filter(None)

		patterns = [ "'%d,%%'", "'%%,%d,%%'", "'%%,%d'" ]
		match = ' OR '.join([ "tags LIKE %s" % p for p in patterns ])
		sql = ' OR '.join(
			[ match % (int(i), int(i), int(i)) for i in tags ])

		return Filter("(%s)" % sql)


class Order(Clause):
	""" An ordering constraint (e.g. ORDER BY date). """

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

	@classmethod
	def locations(cls):
		return Order("location")


class Select:
	""" Get data from the database. """

	def __init__(self,
			filter,
			order = Order.start_date(),
			fields = Fields.events(),
			source = Tables.events()):

		self.where = filter
		self.order = order
		self.fields = fields
		self.source = source

	def execute(self, cursor):
		cursor.execute(self.__str__())
		results = cursor.fetchall()

		conferences = []

		field_names = self.fields.names()
		for result in results:
			conferences.append(
				event.Event(dict(zip(field_names, result))))

		return conferences

	def __str__(self):
		return "SELECT" + self.fields + self.source + self.where + self.order


class Update:
	""" Update data in the database. """

	def __init__(self, table, values, filter):
		self.table = table
		self.values = values
		self.filter = filter

	def execute(self, cursor):
		cursor.execute(self.__str__())
		cursor.connection.commit()

	def __str__(self):
		return "UPDATE" + self.table + self.values + self.filter

