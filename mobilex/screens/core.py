import typing as t



from .base import UssdScreen


class UssdMenuScreen(UssdScreen):

	class Meta:
		abstract = True

	@property
	def header(self):
		return ()

	@property
	def footer(self):
		return ()

	@property
	def menu(self):
		raise AttributeError('menu')

	def handle_input(self, opt):
		return self.menu.handle(opt, self)

	def render_content(self):
		self.render_header()
		self.render_menu()
		self.render_footer()
		return self.CON

	def render_menu(self):
		self.menu.render(self)

	def render_header(self):
		val = self.header
		if not isinstance(val, str) and isinstance(val, t.Iterable):
			for l in val:
				self.print(l)
		else:
			self.print(val)

	def render_footer(self):
		val = self.footer
		if not isinstance(val, str) and isinstance(val, t.Iterable):
			for l in val:
				self.print(l)
		else:
			self.print(val)
