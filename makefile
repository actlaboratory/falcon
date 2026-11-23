run:
	py falcon.py

setup:
	py -m pip install -r requirements.txt
	py -m pip install --no-deps -r requirements-nodeps.txt

fmt:
	py -m autopep8 -r -i -a -a --ignore=E402,E721 --max-line-length 150 .

.PHONY: clear-keymap
clear-keymap:
	rm keymap.ini
.PHONY: bumpup
bumpup:
	py tools\bumpup.py
.PHONY: build
build:
	py tools\build.py
