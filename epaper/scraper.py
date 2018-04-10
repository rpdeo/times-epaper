from PIL import Image
from bs4 import BeautifulSoup
from io import BytesIO
import logging
import random
import requests
import time

# logging
logger = logging.getLogger('scraper')


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
            logger.error('could not retrieve {0}'.format(url))
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
