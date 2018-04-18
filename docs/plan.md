# Current state and Planned Features

## Tests and Test Automation
   - *In Progress*

## Better Data Management
   - *In Progress*

## Code Refactor
   - *In Progress*

## Better Documentation
   - *In Progress*

## Reorganize into a python package
   - *Done*
   - Push to pypi/pypa
     *Scheduled*

## Add logging
   - *DONE*
   - Default application log is at `~/.cache/epaper-app/epaper-app.log`

## Good command line interaction
   - *DONE*
   - Interactive mode supports word-completion for publication and edition selection, press
     TAB at the prompts to see the same choices available as on the website.
   - `click` -based command option processing also added.

## Manage user configuration
   - Added configparser support
     - *DONE*
     - Default config location: `~/.config/epaper-app/config.ini`
   - Selection of Publication and Edition
     - *DONE*
   - Config file update
     - *DONE*
   - Choose between JPGs or PDF page downloads
     - *Scheduled*
     - After UI stablizes and offers option of image or PDF downloads and *display*

## Notifications
   - *DONE*
   - see `utils.notify()`
   - This is still hacky as it calls out to another process based on a
     platform, we might go to full native API libs for better notification
     support.

## Graphical E-Paper Viewer App
   - kivy
     - *DONE*
     - Working kivy GUI exists now
     - It is in a separate repo
     - Might merge here after data management fixes are done.
   - Beeware/Toga
     - *In Progress*
     - see `epaper/toga_app.py`
     - not integrated with downloader yet
     - also only macOS for now with development version of `toga`.
   - GTK
     - *Not planned yet*
     - Might not be need if Toga version works on Linux also.
