from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
from io import BytesIO
from prompt_toolkit import prompt
from prompt_toolkit.contrib.completers import WordCompleter
from .utils import notify
import os
import random
import requests
import sys
import time


SITE = 'https://epaperlive.timesofindia.com/'
SITE_ARCHIVE = 'https://epaperlive.timesofindia.com/Search/Archives'
SITE_ARCHIVE_EDITION = 'https://epaperlive.timesofindia.com/Search/Archives?PUB={pub_code}'


def get_page(url):
    """Get index page of E-paper site."""
    res = requests.get(url)
    if res.status_code == 200:
        doc = BeautifulSoup(res.text, 'html.parser')
        return doc
    else:
        return None


def get_toc(url):
    """Get table of contents as JSON from given `URL`."""
    res = requests.get(url)
    if res.status_code == 200:
        return requests.get(url).json()
    else:
        return None


def parse_publication_codes(doc):
    """Find tag with id='Publications', parse the HTML to obtain tuple of
publication code and publication name. Return list of tuples as a dict.
    """
    publications = []
    for select in doc.find_all(id='Publications'):
        for el in select.find_all('option'):
            publications.append((el.text.strip(), el.get('value').strip()))
    return dict(publications)


def parse_edition_codes(doc):
    """Find tag with id='Editions', parse the HTML to obtain tuple of
edition code and edition name. Return list of tuples as a dict.
    """
    editions = []
    for select in doc.find_all(id='Editions'):
        for el in select.find_all('option'):
            editions.append((el.text.strip(), el.get('value').strip()))
    return dict(editions)


def validate_pages(pages):
    """Validate page information and URL by fetching page json information and HTTP response status code."""
    valid = []

    message = 'Validate page urls...'
    print(message,)

    for page in pages:

        print('\b' * len(message),)
        message = 'Validating page {}'.format(page[1])
        print(message,)

        res = requests.get(page[0] + 'page.json')

        if res.status_code == 200:
            pdf_name = res.json()['pdf']
            valid.append(page +
                         (pdf_name,))

            print('\b' * len(message),)
            message = 'Validated page {}'.format(page[1])
            print(message,)

    return valid


def download_and_save_page_images(pages, download_path):
    num_downloads = 0
    if os.path.exists(download_path):
        for page in pages:
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
                            '{path}/page-{0}.jpg'.format(page[1], path=download_path))
                        num_downloads += 1
                        print('Downloaded page {0}.'.format(page[1]))
                        # success, exit retry loop and go to next page
                        retry_count = retry_limit + 1
                    except IOError as E:
                        # failed, try until retry_limit is exceeded
                        print('Could not save page {0}, attempt {1}'.format(
                            page[1], retry_count))
                        retry_count += 1
                        # we observed truncation of images occasionally...
                        print('Saving raw content to file for inspection.')
                        with open('{path}/page-{0}.dump'.format(page[1], path=download_path),
                                  'wb') as f:
                            f.write(res.content)
                else:
                    print('Could not save page {}, HTTP status code {}'.format(
                        page[1], res.status_code))
                    retry_count += 1
    return num_downloads


def select_publication_and_edition():
    """Select publication and edition interactively."""
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
            os.makedirs(download_path, exist_ok=True)
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
    """Main program: Handle selection of publication and edition codes and execute
page downloads.

    """
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
