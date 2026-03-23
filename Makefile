VENV_DIR    = /opt/nvda_service/venv
PYTHON      = /usr/bin/python3
SERVICE_DIR = /opt/nvda_service

install:
	sudo mkdir -p $(SERVICE_DIR)
	sudo cp nvda_service.py $(SERVICE_DIR)/
	sudo cp nvda.service /etc/systemd/system/
	sudo cp run.sh $(SERVICE_DIR)
	sudo chmod +x run.sh
	sudo ln -sf $(SERVICE_DIR)/state.json ./state.json
	sudo ln -sf $(SERVICE_DIR)/nvda.log ./nvda.log
	sudo systemctl daemon-reload
	sudo systemctl enable --now nvda.service

venv:
	sudo $(PYTHON) -m venv $(VENV_DIR)
	sudo $(VENV_DIR)/bin/pip install --upgrade pip
	sudo $(VENV_DIR)/bin/pip install yfinance exchange-calendars

venv-remove:
	sudo rm -rf $(VENV_DIR)

status:
	sudo systemctl status nvda.service

stop:
	sudo systemctl stop nvda.service

restart:
	sudo systemctl restart nvda.service

update:
	sudo cp nvda_service.py $(SERVICE_DIR)/
	sudo systemctl restart nvda.service

uninstall:
	sudo systemctl stop nvda.service
	sudo systemctl disable nvda.service
	sudo rm -f /etc/systemd/system/nvda.service
	sudo rm -rf $(SERVICE_DIR)
	sudo rm -f ./state.json ./nvda.log
	sudo systemctl daemon-reload

inspect:
	sudo journalctl -u nvda.service -f

inspect-eod:
	sudo journalctl -u nvda.service --no-pager | grep -A 4 "EOD REPORT"

create-symlink:
	sudo ln -sf $(SERVICE_DIR)/state.json ./state.json
	sudo ln -sf $(SERVICE_DIR)/nvda.log ./nvda.log

.PHONY: install venv venv-remove venv-status status stop restart update uninstall inspect inspect-eod create-symlink
