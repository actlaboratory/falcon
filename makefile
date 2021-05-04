run:
	py falcon.py

setup:
	py -m pip install -r requirements.txt

fmt:
	py -m autopep8 -r -i -a -a --ignore=E402,E721 .

.PHONY: clear-keymap
clear-keymap:
	rm keymap.ini
.PHONY: bumpup
bumpup:
	py tools\bumpup.py
.PHONY: build
build:
	py tools\build.py
