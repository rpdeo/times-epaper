# E-Paper Downloader

Simple web-scraper for The Times of India e-paper website.

# Why ?

- Mostly to scratch an itch.
- Data for use with Human Interaction Device Experiments
  - Magic Mirror
  - Rear-projection gesture controlled UI
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

# Plan

- Error logging
- Add command line processing
- Manage User Configuration
  - Selection of Publication Code, Edition Code
  - Choose between JPGs or PDF page downloads
- Notification of download completions
- Beeware-based GUI
