class a(object):
	def test(self):
		print("test a")

class b(object):
	def test(self):
		print("test b")

instance=a()

table={"func": instance.test}
table["func"]()

instance2=instance

instance=b()
table["func"]()
