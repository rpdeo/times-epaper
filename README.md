# Project Status

Backend API's have changed since this was made, so it will not work any ways ...

Development on hold until I have time for this... :)

I have only updated `requirements.txt` to do away with DependABot alerts.

# E-Paper Downloader

Simple python web-scraper for *The Times of India* e-paper publication
archive.

# Why?

- Read the newspaper on a digital device (obviously)
- Data collection for use with Human Interaction Device Experiments
  - Magic Mirror
  - Gesture controlled UI
  - Surface table -like devices etc.
- Explore building cross-platform apps in Python

# Installation

## As a user of the software

``` bash
# Ensure you have python3.6 installed
which `python3.6`

# if you do, continue with steps below
# if not, this software won't work (by design)

# following should install a console script in
# venv/bin/epaper and the python epaper package in
# venv/lib/python3.6/site-packages.
pip3 install https://github.com/rpdeo/times-epaper.git

# simple interactive CLI mode:
# 1. Follow the prompts, tab completion available
# 2. Page images get downloaded to ~/.cache/epaper-app/...
epaper

# non-interactive CLI mode: for advanced users
# Download a specific publication with specific edition
# for a given date
epaper --publication_code XXX --edition_code YYY # optional: --date YYYY-MM-DD

# fully non-interactive CLI mode: for advanced users
# configure once with interactive mode or as above
# every subsequent invocation as below will download
# for today's date
epaper --from_config

# Bonus: configure above command in crontab for daily
# downloads

# GUI landing soon, watch this space.
```

## As a developer, I would do...

``` bash
virtualenv -p `which python3.6` venv
source venv/bin/activate
git clone https://github.com/rpdeo/times-epaper.git
cd times-epaper
pip3 install -e . # install in development mode
epaper # runs from venv/bin/epaper, test it out..
```

# Interaction Testing

- Downloads OK
- Basic command-line functionality OK
- Installs as a python package OK

# Plan Ahead

See [Plan](docs/plan.md)
