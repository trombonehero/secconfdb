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
				'permanentURL AS url', '`meeting-type` AS type_id', 'tags'
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
				"proceedings", "Conferences.permanentURL AS conf_url"
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

	@classmethod
	def meeting_types(cls):
		return Fields([ "`meeting-type` AS type_id", "name" ])


class Values(Clause):
	""" Table values that we wish to set (e.g. foo = 42). """

	def __init__(self, action, values):
		assert values != None
		assert len(values) > 0

		# Put single quotes around strings, convert None to SQL-friendly NULL.
		for (name, value) in values.items():
			if value is None: values[name] = 'NULL'
			elif isinstance(value, basestring): values[name] = "'%s'" % value

		formatted_values = None
		if action == 'SET':
			formatted_values = ', '.join([
					'%s = %s' % (name, value) for (name, value) in values.items() ])

		elif action == 'VALUES':
			formatted_values = '(%s)' % ', '.join(values.values())

		else:
			raise ValueError, "Unknown action '%s'" % action

		Clause.__init__(self, action, formatted_values)


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
	def by_date(cls, min_days, max_days):
		return Filter(
			"startDate BETWEEN ADDDATE(CURDATE(), %d) AND ADDDATE(CURDATE(), %d)"
			% (min_days, max_days))

	@classmethod
	def recent(cls):
		return Filter.by_date(-180, 0)

	@classmethod
	def upcoming(cls):
		return Filter.by_date(0, 365)

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

		match = "tags REGEXP '([0-9]+,)*%d(,[0-9]+)*'"
		sql = ' OR '.join([ match % i for i in tags ])

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

		# Use field names (either from the query, or, in the 'SELECT *' case,
		# from the DB cursor) to construct a dictionary of values.
		field_names = self.fields.names()
		if len(field_names) == 1 and field_names[0] == '*':
			field_names = [ i[0] for i in cursor.description ]

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

class Insert:
	""" Insert a new entry into the database. """

	def __init__(self, table, fields, values):
		self.table = table
		self.fields = fields
		self.values = values

	def execute(self, cursor):
		cursor.execute(self.__str__())
		cursor.connection.commit()

	def __str__(self):
		return "INSERT INTO" + self.table + '(' + self.fields + ')' + self.values

