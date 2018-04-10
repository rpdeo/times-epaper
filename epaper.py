from PIL import Image
from bs4 import BeautifulSoup
from collections import namedtuple
from datetime import datetime, timedelta
from io import BytesIO
from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter
from utils import notify
import configparser
import glob
import json
import logging
import os
import random
import requests
import sys
import time

__version__ = (0, 0, 1)

# logging
logger = logging.getLogger('epaper')

SITE = 'https://epaperlive.timesofindia.com'
SITE_ARCHIVE = 'https://epaperlive.timesofindia.com/Search/Archives?AspxAutoDetectCookieSupport=1'
SITE_ARCHIVE_EDITION = 'https://epaperlive.timesofindia.com/Search/Archives?AspxAutoDetectCookieSupport=1&PUB={pub_code}'


class AppConfig:
    def __init__(self):
        self.config_home = os.path.join(
            os.environ.get('HOME'),
            '.config',
            'epaper-app'
        )

        self.config_file = os.path.join(
            self.config_home,
            'config.ini'
        )

        self.cache_dir = os.path.join(
            os.environ.get('HOME'),
            '.cache',
            'epaper-app'
        )

        self.valid = False

        self.config = configparser.ConfigParser()

        if not os.path.exists(self.config_home):
            os.makedirs(self.config_home)

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            self.validate_config()

        # if no config file found or config read was not valid, create new
        # default config, and save it.
        if not os.path.exists(self.config_file) or \
           not self.valid:
            self.config['App'] = {
                'app_name': 'EPaperApp',
                'app_version': '{0}.{1}.{2}'.format(*__version__),
                'cache_dir': self.cache_dir,
                'log_file': os.path.join(self.cache_dir, 'epaper-app.log')
            }
            self.config['Http'] = {
                'request_delay_min': 15,
                'request_delay_max': 30,
                'user_agent': '/'.join([self.config['App']['app_name'],
                                        self.config['App']['app_version']
                                        ]),
            }
            self.config['Publishers'] = {
                'TOI': ''
            }
            self.config['TOI'] = {
                'site_url': 'https://epaperlive.timesofindia.com',
                'site_archive_url': 'https://epaperlive.timesofindia.com/Search/Archives?AspxAutoDetectCookieSupport=1',
                'selected_pub_code': '',
                'selected_edition_code': ''
            }
            self.save()

    def validate_config(self):
        self.valid = False
        sections = self.config.sections()
        if not sections:
            return
        # damn this is hacky
        a_publisher = ([
            publisher for publisher in self.config['Publishers']][0]).upper()
        # These sections must be present
        if 'App' in sections and \
           'Http' in sections and \
           'Publishers' in sections and \
           a_publisher in sections and \
           self.config['App']['cache_dir'] and \
           self.config['Http']['request_delay_min'] and \
           self.config['Http']['request_delay_max'] and \
           self.config[a_publisher]['site_url'] and \
           self.config[a_publisher]['site_archive_url']:
            self.valid = True

    def save(self):
        '''Validate and save config to config_file.'''
        self.validate_config()
        if self.valid:
            with open(self.config_file, 'w') as fd:
                self.config.write(fd)


class Scraper:
    '''Class encapsulating all scraping related activity.'''

    def __init__(self, publisher=None, app_config=None):
        self.site_url = app_config.config[publisher]['site_url']
        self.site_archive_url = app_config.config[publisher]['site_archive_url']
        self.site_archive_edition_url = '&'.join([
            app_config.config[publisher]['site_archive_url'],
            'PUB={pub_code:s}'
        ])
        self.selected_pub_code = app_config.config[publisher]['selected_pub_code']
        self.selected_edition_code = app_config.config[publisher]['selected_edition_code']

        self.repository_uri_template = 'Repository/{pub_code:s}/{edition_code:s}/{date:s}'

        # requests session object
        self.session = requests.session()

    def _build_repository_uri(self, pub_code=None, edition_code=None, date_str=None):
        '''Return formatted repository uri path.'''
        return self.repository_uri_template.format(
            pub_code=pub_code,
            edition_code=edition_code,
            date=date_str
        )

    def build_toc_url(self, pub_code=None, edition_code=None, date_str=None):
        '''Return formatted toc.json URL path.'''
        return '/'.join([
            self.site_url,
            self._build_repository_uri(
                pub_code=pub_code,
                edition_code=edition_code,
                date_str=date_str
            ),
            'toc.json'
        ])

    def build_page_urls(self, pub_code=None, edition_code=None,
                        date_str=None, page_folder=None):
        '''Return formatted page urls to be downloaded.'''
        page_url = '/'.join([
            self.site_url,
            self._build_repository_uri(
                pub_code=pub_code,
                edition_code=edition_code,
                date_str=date_str
            ),
            page_folder
        ])

        # if we have a valid page_url, get PDF file name
        pdf_url = None
        res = self.fetch(page_url + '/page.json')
        if res:
            pdf_url = page_url + '/' + res['pdf']

        # each value is [url, filename, filename_exists]
        return {
            'thumbnail': [page_url + '/page_thumbnail.jpg', None, False],
            'lowres': [page_url + '/big_page.jpg', None, False],
            'highres': [page_url + '/big_page2.jpg', None, False],
            'pdf': [pdf_url, None, False]
        }

    def fetch(self, url, delay=False):
        '''GET a URL resource once with sleep deplay.'''
        if delay:
            # Be nice; sleep for 15 to 30 seconds between requests; it would
            # take about 8 to 15 mins to download about 30 pages worth. This
            # should be *slow* enough for webmasters to not care.
            sleep_for = random.randint(15, 30)
            time.sleep(sleep_for)
        # fetch
        res = self.session.get(url)
        if res.status_code == 200:
            content_type = res.headers.get('content-type')
            if content_type.startswith('text/html'):
                return BeautifulSoup(res.text, 'html.parser')
            elif content_type.startswith('application/json'):
                return res.json()
            else:
                # probably an image
                return res.content
        else:
            logger.error(f'EPaper: could not retrieve {url}')
            return None

    def save_image(self, url, save_to_file, retry_limit=1, delay=True):
        '''Fetch given URL and save the image with specified retry attempts and random
delay between requests.'''
        retry_count = 1

        if not save_to_file:
            return (False, retry_count)

        while retry_count <= retry_limit:
            content = self.fetch(url, delay=delay)
            if content:
                try:
                    image = Image.open(BytesIO(content))
                    image.save(save_to_file)
                    break
                except IOError as e:
                    retry_count += 1
                    if retry_count > retry_limit:
                        # retries are HTTP success but image has format errors.
                        with open(save_to_file + '.dump', 'wb') as f:
                            f.write(content)
            else:
                retry_count += 1

        if retry_count > retry_limit:
            return (False, retry_count)
        else:
            return (True, retry_count)

    def parse_publication_codes(self, doc):
        '''Find tag with id='Publications', parse the HTML to obtain tuple of
        publication code and publication name. Return list of tuples as a
        dict.

        '''
        publications = []
        for select in doc.find_all(id='Publications'):
            for el in select.find_all('option'):
                publications.append((el.text.strip(), el.get('value').strip()))
        return dict(publications)

    def parse_edition_codes(self, doc):
        '''Find tag with id='Editions', parse the HTML to obtain tuple of edition code
        and edition name. Return list of tuples as a dict.

        '''
        editions = []
        for select in doc.find_all(id='Editions'):
            for el in select.find_all('option'):
                editions.append((el.text.strip(), el.get('value').strip()))
        return dict(editions)


class EPaper:
    '''Manages data that is pulled from SITE_ARCHIVE to enable selection of a specific
publication.'''

    def __init__(self, publisher=None, app_config=None):
        # app config
        self.publisher = publisher
        self.app_config = app_config

        # dict of publication labels and codes
        self.publications = dict([
            ('The Times of India', 'TOI'),
        ])

        # dict of edition labels and codes
        self.editions = dict([
            ('Mumbai', 'BOM'),
        ])

        # selectable dates for epaper download
        self.available_dates = [
            (datetime.today().date() - timedelta(i)).strftime('%Y%m%d') for i in range(1, 8)
        ]

        # publication code and label after selection
        self.selected_publication = ('', '')  # (label, code)

        # edition code and label after selection
        self.selected_edition = ('', '')  # (label, code)

        # epaper date selection, default: today's date
        self.selected_date = datetime.today().date()

        # download area
        self.download_path = ''

        # table of contents for the selected publication: a dict
        self.toc_dict = dict()

        # number of pages in selected epaper
        self.num_pages = 0

        # array index of page being viewed
        self.selected_page = 0

        # page data
        # urls: dict of lists where each key points to [url, filename, exists]
        # see implementation in scraper.build_page_urls()
        # this is can be made better
        self.Page = namedtuple(
            'Page', ['number', 'title', 'urls'])
        self.pages = []

        # publications available in cache
        # each element of list is a tuple(pub_code, edition_code, date_str)
        self.on_disk_pubs = []

    def get_page_image_from_disk(self, page_index, image_type='thumbnail'):
        '''Read and return page image from disk given page_index.'''
        if len(self.pages) > 0:
            page = self.pages[page_index]
            try:
                filename = page.urls[image_type][1]
                if os.path.exists(filename):
                    with open(filename, 'rb') as fd:
                        return Image(BytesIO(fd.read()))
                else:
                    return None
            except IOError as e:
                logger.error('EPaperApp: error reading {fname}')
        return None

    def save_codes_to_config(self):
        pub_code = self.selected_publication[1]
        edition_code = self.selected_edition[1]
        if self.publisher:
            self.app_config.config[self.publisher]['selected_pub_code'] = pub_code
            self.app_config.config[self.publisher]['selected_edition_code'] = edition_code
            self.app_config.save()

    def create_download_dir(self):
        '''Given publication date and pub_code and edition_code, create disk cache path.'''
        pub_code = self.selected_publication[1]
        edition_code = self.selected_edition[1]
        date = self.selected_date
        if (date is not None) and \
           (pub_code is not None) and \
           (pub_code != '') and \
           (edition_code is not None) and \
           (edition_code != ''):
            self.download_path = os.path.join(
                self.app_config.config['App']['cache_dir'],
                pub_code,
                edition_code,
                str(date.date())  # YYYY-MM-DD
            )
            os.makedirs(self.download_path, exist_ok=True)

    def save_page_metadata(self):
        '''Save self.pages after first initial download, so any subsequent redownloads
can restart from this db than re-requesting all data again. This should also
help manage planned sync feature.

        '''
        if len(self.pages) > 0:
            filename = os.path.join(self.download_path, 'page_metadata.json')
            with open(filename, 'w') as fd:
                fd.write(json.dumps(self.pages))

    def find_on_disk_pubs(self):
        '''Find previously downloaded publications within cache directory.'''
        cache_dir = self.app_config.config['App']['cache_dir']
        return [tuple(dirpath.split('/')[-3:])
                for dirpath, dirs, files in os.walk(cache_dir)
                if 'toc.json' in files]

    def load_pub(self, pub_code=None, edition_code=None, date_str=None):
        '''Load self.pages data from json dump in disk cache.'''
        cache_dir = self.app_config.config['App']['cache_dir']
        download_path = os.path.join(
            cache_dir, pub_code, edition_code, date_str)
        toc_filename = os.path.join(download_path, 'toc.json')
        metadata_filename = os.path.join(download_path, 'page_metadata.json')
        if os.path.exists(toc_filename) and \
           os.path.exists(metadata_filename):
            with open(toc_filename, 'r') as fd:
                toc = json.load(fd)
            with open(metadata_filename, 'r') as fd:
                metadata = json.load(fd)
        return (toc, metadata)


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
                    print('\b' * len(self.last_message), end='', flush=True)
                print(message, end=end, flush=flush)
                self.last_message = message


def get_page(url):
    '''Get index page of E-paper site.'''
    res = requests.get(url)
    if res.status_code == 200:
        doc = BeautifulSoup(res.text, 'html.parser')
        return doc
    else:
        return None


def get_toc(url):
    '''Get table of contents as JSON from given `URL`.'''
    res = requests.get(url)
    if res.status_code == 200:
        return requests.get(url).json()
    else:
        return None


def parse_publication_codes(doc):
    '''Find tag with id='Publications', parse the HTML to obtain tuple of
publication code and publication name. Return list of tuples as a dict.
    '''
    publications = []
    for select in doc.find_all(id='Publications'):
        for el in select.find_all('option'):
            publications.append((el.text.strip(), el.get('value').strip()))
    return dict(publications)


def parse_edition_codes(doc):
    '''Find tag with id='Editions', parse the HTML to obtain tuple of
edition code and edition name. Return list of tuples as a dict.
    '''
    editions = []
    for select in doc.find_all(id='Editions'):
        for el in select.find_all('option'):
            editions.append((el.text.strip(), el.get('value').strip()))
    return dict(editions)


def validate_pages(pages):
    '''Validate page information and URL by fetching page json information and HTTP response status code.'''
    valid = []

    message = 'Validate page urls'
    print(message, end='', flush=True)

    for page in pages:

        print('\b' * len(message), end='', flush=True)
        message = 'Validating page {}'.format(page[1])
        print(message, end='', flush=True)

        res = requests.get(page[0] + 'page.json')

        if res.status_code == 200:
            pdf_name = res.json()['pdf']
            valid.append(page +
                         (pdf_name,))

            print('\b' * len(message), end='', flush=True)
            message = 'Validated page {}'.format(page[1])
            print(message, end='', flush=True)

    print(flush=True)
    return valid


def find_missing(pages, download_path):
    '''On a redownload request, check for missing pages and only download those.'''
    existing = glob.glob(os.path.join(download_path, 'page-*-thumbnail.jpg'))
    existing += glob.glob(os.path.join(download_path, 'page-*-highres.jpg'))
    existing += glob.glob(os.path.join(download_path, 'page-*-lowres.jpg'))
    # just return if no pages have bee downloaded yet.
    if len(existing) == 0:
        return pages

    filepaths = []
    for page in pages:
        filepaths.append(
            '{path}/page-{0}-thumbnail.jpg'.format(page[1], path=download_path))
        filepaths.append(
            '{path}/page-{0}-highres.jpg'.format(page[1], path=download_path))
        filepaths.append(
            '{path}/page-{0}-lowres.jpg'.format(page[1], path=download_path))

    # else find missing ones ignoring any '*-lowres.jpg' ones
    missing = set(sorted([p.split('-')[1]
                          for p in (set(filepaths) - set(existing)) if not p.endswith('lowres.jpg')]))
    selected = []
    for m in missing:
        for p in pages:
            if p[1] == m:
                selected.append(p)

    return selected


def download_and_save_page_images(pages, download_path):
    num_downloads = 0
    if os.path.exists(download_path):
        # find missing pages
        pages = find_missing(pages, download_path)

        for page in pages:
            # get page_thumbnail.jpg
            res = requests.get(page[0] + 'page_thumbnail.jpg')
            if res.status_code == 200:
                try:
                    i = Image.open(BytesIO(res.content))
                    i.save(
                        '{path}/page-{0}-thumbnail.jpg'.format(page[1], path=download_path))
                    logger.info(
                        'Downloaded page {0} thumbnail.'.format(page[1]))
                except IOError as E:
                    logger.info(
                        'Could not save thumbnail {0}'.format(page[1]))
                    logger.info('Saving raw content to file for inspection.')
                    with open('{path}/page-{0}-thumbnail.dump'.format(page[1], path=download_path),
                              'wb') as thumbnail:
                        thumbnail.write(res.content)

            # get high-res page
            retry_limit = 3
            retry_count = 1
            while retry_count <= retry_limit:
                # Be nice; sleep for 15 to 30 seconds between requests; it would
                # take about 8 to 15 mins to download about 30 pages worth. This
                # should be *slow* enough for webmasters to not care.
                sleep_for = random.randint(15, 30)
                time.sleep(sleep_for)
                # fetch
                res = requests.get(page[0] + 'big_page2.jpg')
                # check
                if res.status_code == 200:
                    try:
                        i = Image.open(BytesIO(res.content))
                        i.save(
                            '{path}/page-{0}-highres.jpg'.format(page[1], path=download_path))
                        num_downloads += 1
                        logger.info('Downloaded page {0}.'.format(page[1]))
                        # success, exit retry loop and go to next page
                        break
                    except IOError as E:
                        # failed, try until retry_limit is exceeded
                        logger.info('Could not save page {0}, attempt {1}'.format(
                            page[1], retry_count))
                        retry_count += 1

                        # we have observed atleast 1 corrupted highres images
                        # for each download run; save a copy to see whats the reason...
                        if retry_count > retry_limit:
                            logger.info(
                                'Saving raw content to file for inspection.')
                            with open('{path}/page-{0}-highres.dump'.format(page[1], path=download_path),
                                      'wb') as f:
                                f.write(res.content)

                else:
                    logger.info('Could not save page {}, HTTP status code {}'.format(
                        page[1], res.status_code))
                    retry_count += 1

            # lets get the low-resolution page, if all attempts to get highres failed...
            if retry_count > retry_limit:
                res = requests.get(page[0] + 'big_page.jpg')
                if res.status_code == 200:
                    i = Image.open(BytesIO(res.content))
                    i.save(
                        '{path}/page-{0}-lowres.jpg'.format(page[1], path=download_path))
                    num_downloads += 1
                    logger.info(
                        'Downloaded lower-resolution page {0}.'.format(page[1]))

    return num_downloads


def select_publication_and_edition():
    '''Select publication and edition interactively.'''
    pub_code = None
    edition_code = None
    # get index archive page
    doc = get_page(SITE_ARCHIVE)

    if doc:
        # get pub codes and select one
        pub_code_dict = parse_publication_codes(doc)
        pub_code_completer = WordCompleter(pub_code_dict.keys())
        selected_pub_code_key = prompt('Enter publication: ',
                                       completer=pub_code_completer)
        pub_code = pub_code_dict[selected_pub_code_key]
    else:
        return (None, None)

    if pub_code:
        # get edition codes and select one
        doc = get_page(SITE_ARCHIVE_EDITION.format(pub_code=pub_code))

        if doc:
            edition_code_dict = parse_edition_codes(doc)
            edition_code_completer = WordCompleter(edition_code_dict.keys())
            selected_edition_code_key = prompt(
                'Enter Edition/Location: ', completer=edition_code_completer)
            edition_code = edition_code_dict[selected_edition_code_key]
            return (pub_code, edition_code)
        else:
            return (None, None)


def download_epaper(pub_code, edition_code, date=None):
    if date is None:
        date = datetime.today()
    today = '{year:04d}{month:02d}{day:02d}'.format(
        year=date.year, month=date.month, day=date.day)
    repository_path = 'Repository/{pub_code}/{edition_code}/{today}/'.format(
        pub_code=pub_code, edition_code=edition_code, today=today)
    url = SITE + repository_path + 'toc.json'
    page_info = get_toc(url)
    if 'toc' in page_info:
        totalPages = len(page_info['toc'])
        download_path = os.path.abspath('./{pub_code}/{edition_code}/{today}'.format(
            pub_code=pub_code, edition_code=edition_code, today=today))

        # save the toc
        os.makedirs(download_path, exist_ok=True)
        with open(os.path.join(download_path, 'toc.json'), 'w') as toc:
            toc.write(json.dumps(page_info))

        page_url_template = '{site}/Repository/{pub_code}/{edition_code}/{today}/{pageFolder}/'
        pages = [
            (page_url_template.format(
                site=SITE, pub_code=pub_code, edition_code=edition_code,
                today=today, pageFolder=info['page_folder']),
             info['page'],
             info['page_title'])
            for info in page_info['toc']
        ]
        valid_pages = validate_pages(pages)
        if len(valid_pages) > 0:
            logger.info('Downloading {} pages...'.format(len(valid_pages)))
            num_downloads = download_and_save_page_images(
                valid_pages, download_path)
            logger.info('Downloaded {} pages.'.format(num_downloads))
            notify('E-Paper downloaded.',
                   'E-Paper {pub_code}, {edition_code} edition has {num} pages. See file://{path}'.format(
                       pub_code=pub_code, edition_code=edition_code, num=num_downloads, path=download_path))
            return None
        else:
            return False
    else:
        return False


def new_main():
    # Load app configuration
    app_config = AppConfig()

    # setup logging
    logging.basicConfig(
        filename=app_config.config['App']['log_file'],
        filemode='w',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )

    # choose a default publisher
    publisher = 'TOI'

    # Scraper instance
    scraper = Scraper(publisher=publisher, app_config=app_config)

    # UI instance: text-based UI
    ui = UI(publisher=publisher, app_config=app_config, text=True)

    # Data instance
    epaper = EPaper(publisher=publisher, app_config=app_config)

    # Pick a publication
    doc = scraper.fetch(scraper.site_archive_url)
    if doc:
        epaper.publications = scraper.parse_publication_codes(doc)
        epaper.selected_publication = ui.select_publication(
            epaper.publications,
            default=app_config.config[publisher].get(
                'selected_pub_code', None)
        )
    else:
        return False

    # Pick an edition
    doc = scraper.fetch(
        scraper.site_archive_edition_url.format(
            pub_code=epaper.selected_publication[1]))

    if doc:
        epaper.editions = scraper.parse_edition_codes(doc)
        epaper.selected_edition = ui.select_edition(
            epaper.editions,
            default=app_config.config[publisher].get(
                'selected_edition_code', None)
        )
    else:
        return False

    if epaper.selected_publication[1] == '' or \
       epaper.selected_edition[1] == '':
        return False

    epaper.save_codes_to_config()

    # Pick a date,
    # XXX: date may not be required for some editions...
    epaper.selected_date = ui.select_pub_date()

    # $HOME/cache_dir/pub/edition/date
    epaper.create_download_dir()

    # inform ui
    ui.download_path = epaper.download_path

    logger.info('Downloading epaper...')
    logger.info('pub_code={0}, edition={1}, date={2}'.format(
        epaper.selected_publication[1],
        epaper.selected_edition[1],
        str(epaper.selected_date.date())
    ))

    date_str = '{year:04d}{month:02d}{day:02d}'.format(
        year=epaper.selected_date.year,
        month=epaper.selected_date.month,
        day=epaper.selected_date.day
    )

    toc_url = scraper.build_toc_url(
        pub_code=epaper.selected_publication[1],
        edition_code=epaper.selected_edition[1],
        date_str=date_str
    )

    epaper.toc_dict = scraper.fetch(toc_url)

    # check for valid dict format.
    if 'toc' not in epaper.toc_dict:
        logger.error('TOC JSON format error! exiting...')
        return False

    # save the toc to default download location
    toc_file = os.path.join(epaper.download_path, 'toc.json')
    with open(toc_file, 'w') as toc:
        toc.write(json.dumps(epaper.toc_dict))

    epaper.num_pages = len(epaper.toc_dict['toc'])

    # build the epaper.pages list of epaper.Page structures
    for i, page in enumerate(epaper.toc_dict['toc']):
        ui.update_status(
            message='Retrieving page {0} metadata'.format(i),
            end='',
            flush=True
        )

        urls = scraper.build_page_urls(
            pub_code=epaper.selected_publication[1],
            edition_code=epaper.selected_edition[1],
            date_str=date_str,
            page_folder=page['page_folder']
        )

        urls['thumbnail'][1] = os.path.join(
            epaper.download_path, 'page-{0:03d}-thumbnail.jpg'.format(int(page['page'])))
        urls['lowres'][1] = os.path.join(
            epaper.download_path, 'page-{0:03d}-lowres.jpg'.format(int(page['page'])))
        urls['highres'][1] = os.path.join(
            epaper.download_path, 'page-{0:03d}-highres.jpg'.format(int(page['page'])))
        urls['pdf'][1] = os.path.join(
            epaper.download_path, 'page-{0:03d}-highres.pdf'.format(int(page['page'])))

        epaper.pages.append(
            epaper.Page(
                number=int(page['page']),
                title=page['page_title'],
                urls=urls
            )
        )

    ui.update_status(
        message='Downloading pages...',
        end='',
        flush=True
    )
    # download required pages
    for i, page in enumerate(epaper.pages):
        page_downloads = 0
        for j, url_key in enumerate(page.urls):
            url = page.urls[url_key][0]
            filename = page.urls[url_key][1]
            file_exists = page.urls[url_key][2]

            if file_exists:
                continue

            if url_key == 'pdf':
                continue

            status, count = scraper.save_image(url, filename)
            if status:
                page_downloads += 1
                # update file_exists flag in epaper.pages
                if os.path.exists(filename):
                    epaper.pages[i].urls[url_key][2] = True
        # track
        if page_downloads >= 2:
            # successful download and save of thumbnail and at least one of
            # low or highres images.
            ui.num_downloads += 1
            ui.update_status(
                message='Downloaded page {}'.format(page.number),
                end='',
                flush=True
            )
        else:
            # note failed attempts
            ui.failed.append(page.number)
            ui.update_status(
                message='Failed to downloaded page {}'.format(page.number),
                end='',
                flush=True
            )

    # final counts
    ui.update_status(message='Downloaded {0} pages.'.format(ui.num_downloads))
    if len(ui.failed) > 0:
        ui.update_status(message='Failed to download {0} pages: {1}'.format(
            len(ui.failed), repr(ui.failed)))

    # save page metadata as json, so UI tools can read it.
    epaper.save_page_metadata()

    # notify
    ui.notify(
        publication=epaper.selected_publication[0],
        edition=epaper.selected_edition[0]
    )


def main(pub_code, edition_code, select_edition=False):
    '''Main program: Handle selection of publication and edition codes and execute
page downloads.

    '''
    on_date = datetime.today()
    if select_edition:
        pub_code, edition_code = select_publication_and_edition()
        # exit if we could not select either publication or edition codes for some reason.
        if pub_code is None or edition_code is None:
            return False

        # now, get desired archive date
        retry = True
        while retry:
            try:
                date_string = prompt(
                    'Enter a date [YYYY-MM-DD]: ', default=datetime.today().strftime('%Y-%m-%d'))
                on_date = datetime.strptime(date_string, '%Y-%m-%d')
                if on_date.date() <= datetime.today().date():
                    retry = False
                else:
                    raise ValueError
            except ValueError:
                print('Please enter date as YYYY-MM-DD including "-".')
                print('Also date must be either today\'s or in the past.')
                retry = True

    logger.info('Downloading epaper...')
    logger.info('pub_code={0}, edition={1}, date={2}'.format(
        pub_code, edition_code, str(on_date.date())))

    return download_epaper(pub_code, edition_code, date=on_date)


if __name__ == '__main__':
    if len(sys.argv) > 2:
        # for calling from cron etc.
        pub_code = sys.argv[1]
        edition_code = sys.argv[2]
        sys.exit(main(pub_code, edition_code))
    else:
        # command-line interaction
        pub_code = None
        edition_code = None
        select_edition = True
        # sys.exit(main(pub_code, edition_code,
        #                  select_edition=select_edition))
        sys.exit(new_main())
