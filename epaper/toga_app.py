import toga
from toga.style.pack import Pack, COLUMN, ROW

import logging

from epaper import EPaper
from appconfig import AppConfig
from scraper import Scraper


class EpaperApp(toga.App):

    logger = logging.getLogger('toga_app')

    def startup(self):
        # choose a default publisher
        self.publisher = 'TOI'

        # Load App configuration from default location
        self.app_config = AppConfig()

        # setup logging
        logging.basicConfig(
            filename=self.app_config.config['App']['log_file'],
            filemode='w',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.DEBUG
        )

        # Scraper
        self.scraper = Scraper(
            publisher=self.publisher,
            app_config=self.app_config
        )

        # Data object instances
        self.epaper = EPaper(
            publisher=self.publisher,
            app_config=self.app_config
        )

        # GUI
        self._menu_items = {}
        self.document_types = ['.jpg', '.png', '.pdf']
        self.main_window = toga.MainWindow(self.name)

        # Get publications
        doc = self.scraper.fetch(self.scraper.site_archive_url)
        if doc:
            self.epaper.publications = self.scraper.parse_publication_codes(
                doc)

        # Get previously selected publication from config or None
        val = self.app_config.config[self.publisher].get(
            'selected_pub_code', '')
        if val:
            self.epaper.selected_publication = [
                p for p in self.epaper.publications.items() if p[1] == val
            ][0]

        # Publication Selection widget
        self.publication_selection = toga.Selection(
            items=self.epaper.publications.keys(),
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )

        # Get editions
        doc = self.scraper.fetch(
            self.scraper.site_archive_edition_url.format(
                pub_code=self.epaper.selected_publication[1]))
        if doc:
            self.epaper.editions = self.scraper.parse_edition_codes(
                doc)

        # Get previously selected edition from config or None
        val = self.app_config.config[self.publisher].get(
            'selected_edition_code', '')
        if val:
            self.epaper.selected_edition = [
                e for e in self.epaper.editions.items() if e[1] == val
            ][0]

        self.edition_selection = toga.Selection(
            items=self.epaper.editions.keys(),
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )

        self.date_selection = toga.Selection(
            items=self.epaper.available_dates,
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )

        # Thumbnail View Commands
        thumbnail_commands = []
        for i in range(self.epaper.num_pages):
            thumbnail_commands.append(
                toga.Command(
                    self.display_page(None, i),
                    label='Display Page',
                    tooltip='Display Page {}'.format(i),
                    group=toga.Group.VIEW,
                    section=0
                )
            )

        thumbnail_buttons = [
            toga.Button(
                'Page {}'.format(i),
                on_press=self.display_page(None, i),
                style=Pack(
                    width=100,
                    padding=2
                )
            ) for i in range(self.epaper.num_pages)
        ]

        # left view of SplitContainer below
        self.thumbnail_view = toga.ScrollContainer(
            content=toga.Box(
                children=thumbnail_buttons,
                style=Pack(
                    direction=COLUMN
                )
            )
        )

        # right view of SplitContainer below
        self.page_view = toga.ScrollContainer(
            content=toga.ImageView(
                id='page-view',
                image=self.epaper.get_page_image_from_disk(
                    self.epaper.selected_page),
            )
        )

        # MainWindow view
        box = toga.Box(
            children=[
                toga.Box(
                    children=[
                        self.publication_selection,
                        self.edition_selection,
                        self.date_selection
                    ],
                    style=Pack(
                        direction=ROW,
                        padding=5
                    )
                ),
                toga.SplitContainer(
                    content=(
                        self.thumbnail_view,
                        self.page_view
                    ),
                    style=Pack(
                        direction=ROW,
                        padding=5
                    )
                )
            ],
            style=Pack(
                direction=COLUMN
            )
        )

        self.main_window.content = box
        self.main_window.show()

    def open_document(self, fileUrl):
        pass

    def display_page(self, sender, page_number):
        """Display page image identified by `page_number`."""
        print(f'Displaying page {page_number}')
        return None


def main():
    return EpaperApp('E-Paper App', 'org.rpdlabs.epaper')


if __name__ == '__main__':
    main().main_loop()
