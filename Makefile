# Start and stop Toponux in the background.
# Options: make start PORT=9000 ARGS=--no-browser
PORT ?= 8765
ARGS ?=
APP := .venv/bin/toponux
PID_FILE := .toponux.pid
LOG_FILE := .toponux.log

# True only if the recorded PID still belongs to Toponux (PIDs get reused).
RUNNING = [ -f $(PID_FILE) ] && grep -qa toponux /proc/$$(cat $(PID_FILE))/cmdline 2>/dev/null

.DEFAULT_GOAL := help
.PHONY: help install start stop restart status

help:
	@echo "make install | start | stop | restart | status"

$(APP):
	@if [ $$(id -u) = 0 ]; then echo "Run 'make install' without sudo first."; exit 1; fi
	python3 -m venv .venv
	.venv/bin/pip install -e .

install: $(APP)

start: $(APP)
	@if $(RUNNING); then echo "Toponux is already running (PID $$(cat $(PID_FILE)))."; exit 0; fi; \
	rm -f $(PID_FILE) $(LOG_FILE); install -m 600 /dev/null $(LOG_FILE); \
	nohup $(APP) --port $(PORT) $(ARGS) >> $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE); chmod 644 $(PID_FILE); \
	sleep 2; \
	if $(RUNNING); then echo "Toponux started: http://127.0.0.1:$(PORT) (PID $$(cat $(PID_FILE)))."; \
	else echo "Toponux failed to start:"; cat $(LOG_FILE); rm -f $(PID_FILE); exit 1; fi

stop:
	@if $(RUNNING); then \
		kill $$(cat $(PID_FILE)) 2>/dev/null || { echo "Cannot stop Toponux. Started with sudo? Run: sudo make stop"; exit 1; }; \
		echo "Toponux stopped."; \
	else echo "Toponux is not running."; fi; \
	rm -f $(PID_FILE)

restart:
	@$(MAKE) --no-print-directory stop
	@$(MAKE) --no-print-directory start

status:
	@if $(RUNNING); then echo "Toponux is running (PID $$(cat $(PID_FILE)))."; else echo "Toponux is not running."; fi
