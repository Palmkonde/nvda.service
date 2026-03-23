# nvda.service

A lightweight systemd service that tracks NVDA stock price in the background.

- Fetches price every 60s during market hours (Mon–Fri 9:30–16:00 Eastern)
- Logs daily min/max + change vs previous close at 4 PM
- Persists state across reboots — catches up on missed EOD reports at startup

## Requirements

- Linux with systemd
- Python 3.9+

## Install

### With python global environment
```bash
git clone https://github.com/Palmkonde/nvda.service.git
cd nvda.service
pip install -r requirements.txt
make install
```

### Python virtual environment
```bash
git clone https://github.com/Palmkonde/nvda.service.git
cd nvda.service
make venv
make install
```

## Usage

```bash
# for venv version 
make install        # deploy service
make venv           # create venv + install yfinance
make venv-remove    # tear down venv, falls back to system python

make status        # check if service is running
make inspect       # live logs
make inspect-eod   # EOD reports only
make update        # deploy latest code changes
make restart       # restart the service
make stop          # stop the service
make uninstall     # remove everything
```

## Logs

Symlinked into the project folder after `make install`:

- `nvda.log` — full log file
- `state.json` — persisted price state
