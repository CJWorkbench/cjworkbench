REPORTER = spec

test:
	./node_modules/.bin/mocha --recursive --reporter $(REPORTER) --require should
test-w:
	./node_modules/.bin/mocha --recursive --reporter $(REPORTER) --require should --watch

.PHONY: test test-w