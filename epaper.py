from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
from io import BytesIO
import codecs
import json
import os
import random
import requests
import sys
import time


SITE = 'https://epaperlive.timesofindia.com/'


def mkdirp(path):
    """Create directory hierarchy, by resolving the absolute path from *path*.
But really use os.makedirs(path, exist_ok=True) rather than this.
"""
    stack = []
    current = os.path.abspath(path)
    while not os.path.isdir(current):
        stack.append(current)
        current = os.path.dirname(current)

    while len(stack) > 0:
        current = stack.pop()
        os.mkdir(current)


def get_main_page_test():
    data = ''
    with open('tests/doc.html', 'r') as f:
        data = f.read()
    doc = BeautifulSoup(data, 'html.parser')
    return doc


def get_toc_test():
    with open('tests/toc.json', 'rb') as f:
        return json.loads(f.read().strip(codecs.BOM_UTF8).strip())


def get_main_page(url):
    """Get index page of E-paper site."""
    data = requests.get(url)
    doc = BeautifulSoup(data, 'html.parser')
    return doc


def get_toc(url):
    """Get table of contents as JSON from given `URL`."""
    return requests.get(url).json()


def parse_publication_codes(doc):
    """Find tag with id='Publications', parse the HTML to obtain tuple of
publication code and publication name. Return list of tuples as a dict.
    """
    publications = []
    for select in doc.find_all(id='Publications'):
        for el in select.find_all('option'):
            publications.append((el.get('value').strip(), el.text.strip()))
    return dict(publications)


def parse_edition_codes(doc):
    """Find tag with id='Editions', parse the HTML to obtain tuple of
edition code and edition name. Return list of tuples as a dict.
    """
    editions = []
    for select in doc.find_all(id='Editions'):
        for el in select.find_all('option'):
            editions.append((el.get('value').strip(), el.text.strip()))
    return dict(editions)


def validate_pages(pages):
    """Validate page information and URL by using HEAD requests and HTTP response status code."""
    valid = []
    for page in pages:
        res = requests.get(page[0] + 'page.json')
        if res.status_code == 200:
            pdf_name = res.json()['pdf']
            valid.append(page +
                         (pdf_name,))
    return valid


def download_and_save_page_images(pages, download_path):
    num_downloads = 0
    if os.path.exists(download_path):
        for page in pages:
            res = requests.get(page[0] + 'big_page2.jpg')
            if res.status_code == 200:
                try:
                    i = Image.open(BytesIO(res.content))
                    i.save(
                        '{path}/page-{0}.jpg'.format(page[1], path=download_path))
                    num_downloads += 1
                except IOError as E:
                    print('Could not save page {}'.format(page[1]))
                    print('Saving raw content to file for inspection.')
                    with open('{path}/page-{0}.dump'.format(page[1], path=download_path),
                              'wb') as f:
                              f.write(res.content)
                    continue

            # Be nice; sleep for 15 to 30 seconds between requests; it would
            # take about 8 to 15 mins to download about 30 pages worth. This
            # should be *slow* enough for webmasters to not care.

            sleep_for = random.randint(15, 30)
            time.sleep(sleep_for)
    return num_downloads


def select_publication_and_edition():
    doc = get_main_page(SITE)
    publications = parse_publication_codes(doc)
    editions = parse_edition_codes(doc)


def download_epaper(pubCode, editionCode, date=None):
    if date is None:
        date = datetime.today()
    today = '{year:04d}{month:02d}{day:02d}'.format(
        year=date.year, month=date.month, day=date.day)
    repository_path = '/Repository/{pubCode}/{editionCode}/{today}/'.format(
        pubCode=pubCode, editionCode=editionCode, today=today)
    url = SITE + repository_path + 'toc.json'
    page_info = get_toc(url)
    if 'toc' in page_info:
        totalPages = len(page_info['toc'])
        download_path = os.path.abspath('./{pubCode}/{editionCode}/{today}'.format(
            pubCode=pubCode, editionCode=editionCode, today=today))
        page_url_template = '{site}/Repository/{pubCode}/{editionCode}/{today}/{pageFolder}/'
        pages = [
            (page_url_template.format(
                site=SITE, pubCode=pubCode, editionCode=editionCode,
                today=today, pageFolder=info['page_folder']),
             info['page'],
             info['page_title'])
            for info in page_info['toc']
        ]
        valid_pages = validate_pages(pages)
        if len(valid_pages) > 0:
            os.makedirs(download_path, exist_ok=True)
            num_downloads = download_and_save_page_images(
                valid_pages, download_path)
            print('Downloaded {} pages.'.format(num_downloads))
            return None
        else:
            return False
    else:
        return False


def main(pubCode, editionCode):
    """Main execution flow of the program."""
    return download_epaper(
        pubCode,
        editionCode,
        date=datetime.today()
    )


if __name__ == '__main__':
    pubCode = sys.argv[1]
    editionCode = sys.argv[2]
    sys.exit(main(pubCode, editionCode))
