.PHONY: install install-dev test typecheck

install:
	sudo pip install --break-system-packages -r requirements.txt
	sudo pip install --break-system-packages -e .

install-dev:
	sudo pip install --break-system-packages -r requirements.txt
	sudo pip install --break-system-packages -r dev.requirements.txt
	sudo pip install --break-system-packages -e .

test:
	python3 -m unittest discover test

typecheck:
	python3 -m pyright
