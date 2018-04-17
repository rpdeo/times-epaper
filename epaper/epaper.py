from PIL import Image
from collections import namedtuple
from datetime import datetime, timedelta
from io import BytesIO
import json
import logging
import os

# logging
logger = logging.getLogger('epaper')


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

        # epaper date selection, default: today's datetime object
        self.selected_date = datetime.today()

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
