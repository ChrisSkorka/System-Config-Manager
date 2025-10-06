.PHONY: install install-dev test

install:
	pip install --break-system-packages -r requirements.txt
	pip install --break-system-packages -e .

install-dev:
	pip install --break-system-packages -r requirements.txt
	pip install --break-system-packages -r dev.requirements.txt
	pip install --break-system-packages -e .

test:
	python3 -m unittest discover test