# E-Paper Downloader

Simple python web-scraper for *The Times of India* e-paper publications.

# Why?

- Read the paper - obviously
- Scratch an itch / one-off / are-the-brain-cells-still-working... kind of project
- Data collection for use with Human Interaction Device Experiments
  - Magic Mirror
  - Gesture controlled UI
  - Surface table-like devices etc.

# Proposed Setup

- Use a low-power device at home like an RPI or your laptop for on-the-go setup.
- Launch via cron.
- Notification via DBUS/Growl/Email etc.

``` bash
git clone $repo
virtualenv -p `which python3` venv
source venv/bin/activate
pip install -r requirements.txt
# single run - defaults to today's date
python epaper.py 'Publication Code' 'Edition Code'
# Examples:
# python epaper.py 'TOI' 'BOM'
# python epaper.py 'ETE' 'ETW' # only on Mondays
```

# Testing

- Fully untested for now, will update on it soonish...

# Plan

- Add logging of actions
- Add kickass command line processing
- Manage User Configuration
  - Selection of Publication Code, Edition Code
  - Choose between JPGs or PDF page downloads
- Notification of download completions via DBUS/Growl/Email etc.
- Beeware-based GUI for viewing the pages
