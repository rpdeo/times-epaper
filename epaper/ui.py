from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter
from epaper.utils import notify
from datetime import datetime
import logging

# logging
logger = logging.getLogger('ui')


class UI:
    '''User Interface Abstration: For text we use prompt_toolkit, for gui we may
use pygtk or beeware/toga or kivy, touch interaction will be enabled if
supported by underlying GUI toolkit.

    '''

    def __init__(self, publisher=None, app_config=None, text=False, gui=False, touch=False):
        # ui types supported
        if text:
            self.text_ui = True
            self.gui = False
            self.touch_ui = False
        if gui:
            self.text_ui = False
            self.gui = True
            self.touch_ui = touch
        if touch:
            self.text_ui = False
            self.gui = True
            self.touch_ui = True

        # app config
        self.publisher = publisher
        self.app_config = app_config

        # empty if not set in config
        self.selected_pub_code = self.app_config.config[self.publisher].get(
            'selected_pub_code', '')
        self.selected_edition_code = self.app_config.config[self.publisher].get(
            'selected_edition_code', '')

        # download_path
        self.download_path = ''

        # successful downloads of pages
        self.num_downloads = 0

        # page numbers for failed attempts
        self.failed = []

        # status updates for ui
        self.last_message = ''

    def select_publication(self, publications, default=None):
        '''Select publication code and label.'''
        pub_code_completer = WordCompleter(publications.keys())
        if default:
            default_key = [
                k for k in publications if publications[k] == default][0]
            pub_code_key = prompt('Enter publication: ',
                                  completer=pub_code_completer,
                                  default=default_key)
        else:
            pub_code_key = prompt('Enter publication: ',
                                  completer=pub_code_completer)
        return (pub_code_key, publications[pub_code_key])

    def select_edition(self, editions, default=None):
        '''Select edition code and label.'''
        edition_code_completer = WordCompleter(editions.keys())
        if default:
            default_key = [
                k for k in editions if editions[k] == default][0]
            edition_code_key = prompt('Enter Edition/Location: ',
                                      completer=edition_code_completer,
                                      default=default_key)
        else:
            edition_code_key = prompt('Enter Edition/Location: ',
                                      completer=edition_code_completer)
        return (edition_code_key, editions[edition_code_key])

    def select_pub_date(self):
        '''Prompt for a date string, check if it is either today's or in the past
and return a datetime object.'''
        on_date = datetime.today()
        retry = True
        while retry:
            try:
                date_str = prompt(
                    'Enter a date [YYYY-MM-DD]: ', default=datetime.today().strftime('%Y-%m-%d'))
                on_date = datetime.strptime(date_str, '%Y-%m-%d')
                if on_date.date() <= datetime.today().date():
                    retry = False
                else:
                    raise ValueError
            except ValueError:
                print('Please enter date as YYYY-MM-DD including "-".')
                print('Also date must be either today\'s or in the past.')
                retry = True
        return on_date

    def notify(self, publication=None, edition=None):
        title = '{edition} edition of {publication} downloaded.'.format(
            publication=publication,
            edition=edition
        )
        message = 'It has {num} pages. Stored at {path}'.format(
            num=self.num_downloads,
            path=self.download_path
        )
        notify(title=title, message=message)

    def update_status(self, message=None, end='\n', flush=False):
        '''Mostly print() wrapper for now.'''
        if message:
            if self.text_ui:
                if self.last_message:
                    print(('\b' * len(self.last_message)), end='', flush=True)
                print(message, end=end, flush=flush)
                self.last_message = message
