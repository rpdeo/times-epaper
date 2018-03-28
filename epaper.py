from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from io import BytesIO
from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter
from utils import notify
import os
import random
import requests
import sys
import time
import json
import glob


SITE = 'https://epaperlive.timesofindia.com/'
SITE_ARCHIVE = 'https://epaperlive.timesofindia.com/Search/Archives'
SITE_ARCHIVE_EDITION = 'https://epaperlive.timesofindia.com/Search/Archives?PUB={pub_code}'


class Scraper(object):
    def __init__(self):
        self.site_url = 'https://epaperlive.timesofindia.com'
        self.site_archive_url = 'https://epaperlive.timesofindia.com/Search/Archives'
        self.site_archive_edition_url = 'https://epaperlive.timesofindia.com/Search/Archives?PUB={pub_code:s}'
        self.repository_uri_template = '/Repository/{pub_code:s}/{edition_code:s}/{date:s}'

        # page info from toc.json
        self.page_info = None

        # pages structure
        self.pages = dict()

    def get_repository_uri(self, pub_code, edition_code, date_str):
        return self.repository_uri_template.format(
            pub_code=pub_code,
            edition_code=edition_code,
            date=date_str
        )

    def get_toc_uri(self, pub_code, edition_code, date_str):
        return '/'.join([
            self.site_url,
            self.get_repository_uri(
                pub_code,
                edition_code,
                date_str
            ),
            'toc.json'
        ])

    def fetch(self, url):
        '''GET a URL resource once with sleep deplay.'''
        # Be nice; sleep for 15 to 30 seconds between requests; it would
        # take about 8 to 15 mins to download about 30 pages worth. This
        # should be *slow* enough for webmasters to not care.
        sleep_for = random.randint(15, 30)
        time.sleep(sleep_for)
        # fetch
        res = requests.get(url)
        if res.status_code == 200:
            if res.content_type == 'text/html':
                return BeautifulSoup(res.text, 'html.parser')
            elif res.content_type == 'application/json':
                return res.json()
            else:
                return res.content
        else:
            print(f'EPaper: could not retrieve {url}')
            return None

    def save_image(self, url, save_to_file, retry_limit=1):
        '''GET an image URL with retry attempts.'''
        retry_count = 1

        if not save_to_file:
            return (False, retry_count)

        while retry_count <= retry_limit:
            content = self.fetch(url)
            if content is None:
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

    def validate_pages(self):
        '''Validate page information and URL by fetching page json information and HTTP response status code.'''
        valid = []

        message = 'Validate page urls'
        print(message, end='', flush=True)

        for page in self.pages:
            print('\b' * len(message), end='', flush=True)
            message = 'Validating page {0:02d}'.format(int(page[1]))
            print(message, end='', flush=True)

            res = self.fetch(page[0] + 'page.json')
            if res:
                pdf_name = res['pdf']
                valid.append(page + (pdf_name,))

            print('\b' * len(message), end='', flush=True)
            message = 'Validated page {0:02d}'.format(int(page[1]))
            print(message, end='', flush=True)

        print(flush=True)
        return valid


class EPaper(object):
    '''Manages data that is pulled from SITE_ARCHIVE to enable selection of a specific
publication.'''

    def __init__(self):
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

        # number of pages in selected epaper
        self.num_pages = 0

        # Paths of downloaded page thumbnails
        self.thumbnail_paths = [None for i in range(self.num_pages)]

        # Paths of downloaded page images
        self.page_paths = [None for i in range(self.num_pages)]

        # array index of page being viewed
        self.selected_page = 0

        # page data
        self.pages = []

    def read_page_image(self, page_index):
        if len(self.page_paths) > 0:
            fname = self.page_paths[page_index]
            try:
                with open(fname, 'rb') as fd:
                    return Image(BytesIO(fd.read()))
            except IOError as e:
                print('EPaperApp: error reading {fname}')
        return None

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
    existing = glob.glob(download_path +
                         os.path.sep + 'page-*-thumbnail.jpg')
    existing += glob.glob(download_path +
                          os.path.sep + 'page-*-highres.jpg')
    existing += glob.glob(download_path +
                          os.path.sep + 'page-*-lowres.jpg')
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
                    print('Downloaded page {0} thumbnail.'.format(page[1]))
                except IOError as E:
                    print('Could not save thumbnail {0}'.format(page[1]))
                    print('Saving raw content to file for inspection.')
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
                        print('Downloaded page {0}.'.format(page[1]))
                        # success, exit retry loop and go to next page
                        break
                    except IOError as E:
                        # failed, try until retry_limit is exceeded
                        print('Could not save page {0}, attempt {1}'.format(
                            page[1], retry_count))
                        retry_count += 1

                        # we have observed atleast 1 corrupted highres images
                        # for each download run; save a copy to see whats the reason...
                        if retry_count > retry_limit:
                            print('Saving raw content to file for inspection.')
                            with open('{path}/page-{0}-highres.dump'.format(page[1], path=download_path),
                                      'wb') as f:
                                f.write(res.content)

                else:
                    print('Could not save page {}, HTTP status code {}'.format(
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
                    print(
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
    repository_path = '/Repository/{pub_code}/{edition_code}/{today}/'.format(
        pub_code=pub_code, edition_code=edition_code, today=today)
    url = SITE + repository_path + 'toc.json'
    page_info = get_toc(url)
    if 'toc' in page_info:
        totalPages = len(page_info['toc'])
        download_path = os.path.abspath('./{pub_code}/{edition_code}/{today}'.format(
            pub_code=pub_code, edition_code=edition_code, today=today))

        # save the toc
        os.makedirs(download_path, exist_ok=True)
        with open(os.path.sep.join([download_path, 'toc.json']), 'w') as toc:
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
            print('Downloading {} pages...'.format(len(valid_pages)))
            num_downloads = download_and_save_page_images(
                valid_pages, download_path)
            print('Downloaded {} pages.'.format(num_downloads))
            notify('E-Paper downloaded.',
                   'E-Paper {pub_code}, {edition_code} edition has {num} pages. See file://{path}'.format(
                       pub_code=pub_code, edition_code=edition_code, num=num_downloads, path=download_path))
            return None
        else:
            return False
    else:
        return False


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
    #
    print('Downloading epaper...\npub_code={0}, edition={1}, date={2}'.format(
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
        sys.exit(main(pub_code, edition_code, select_edition=select_edition))
