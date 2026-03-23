install:
	sudo mkdir -p /opt/nvda_service
	sudo cp nvda_service.py /opt/nvda_service/
	sudo cp nvda.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable --now nvda.service

status:
	sudo systemctl status nvda.service

stop:
	sudo systemctl stop nvda.service

restart:
	sudo systemctl restart nvda.service

update:
	sudo cp nvda_service.py /opt/nvda_service/
	sudo systemctl restart nvda.service

uninstall:
	sudo systemctl stop nvda.service
	sudo systemctl disable nvda.service
	sudo rm -f /etc/systemd/system/nvda.service
	sudo rm -rf /opt/nvda_service
	sudo rm -f $(pwd)/state.json $(pwd)/nvda.log
	sudo systemctl daemon-reload

inspect:
	sudo journalctl -u nvda.service -f

inspect-eod:
	sudo journalctl -u nvda.service --no-pager | grep -A 4 "EOD REPORT"

create-symlink:
	sudo ln -sf /opt/nvda_service/state.json $(pwd)/state.json
	sudo ln -sf /opt/nvda_service/nvda.log $(pwd)/nvda.log

