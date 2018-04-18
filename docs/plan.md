# Plan
  - Tests
    *In Progress*
  - Better Data Management
    *In Progress*
  - Refactor code
    *In Progress*
  - Better Documentation
    *In Progress*
  - Reorganize into a python package
    *Done*
    - Push to pypi/pypa
      *Scheduled*
  - Add logging of actions
    - *DONE*
  - Add kickass command line processing
    - *DONE*
    - Interactive mode supports word-completion for publication and edition selection, press
      TAB at the prompts to see the same choices available as on the website.
    - Click based command option processing also added.
  - Manage User Configuration
    - Added configparser support
      - *DONE*
    - Selection of Publication Code, Edition Code
      - *DONE*
    - Config file update
      - *DONE*
    - Choose between JPGs or PDF page downloads
      - *Scheduled*
      - After UI stablizes and offers option of image or PDF downloads and display
  - Notifications via macOS Notifications, DBUS on Linux, etc.
    - *DONE*
    - see `utils.notify()`
    - This is still hacky, we might go to full native API libs for better
      notifications.
  - Graphical E-Paper Viewer App
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
