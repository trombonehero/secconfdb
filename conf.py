class ConferenceInstance:
	def __init__(self, data):
		assert data is not None
		assert len(data) > 0

		self.__dict__.update(data)


	def when(self):
		""" Pretty-printed date (e.g. 27 Feb-2 Mar 2012). """

		if not self.__dict__.has_key('startDate'): return None

		start = self.startDate
		end = self.endDate

		s = None

		if start.year != end.year: s = start.strftime("%d %b %Y").lstrip("0")
		elif start.month != end.month: s = start.strftime("%d %b").lstrip("0")
		elif start.day != end.day: s = str(start.day)

		if s is None: s = ""
		else: s += "-"

		s += end.strftime("%d %b %Y").lstrip("0")
		return s


	def where(self):
		location = (self.location, self.region, self.country)
		return ", ".join(
			[ unicode(i, "utf8") for i in location if i is not None ])


	def format_deadline(self, which = None):
		print "looking for the '%s' deadine" % which

		date = None
		if which is None: date = self.deadline
		else: date = self.__dict__[which + "Deadline"]

		if date is None: return ""
		return date.strftime("%d %b %Y").lstrip("0")


	def __str__(self):
		return "%s: %s in %s" % (self.abbreviation, self.when(), self.where())
		
	def __repr__(self):
		return repr(self.__dict__)

