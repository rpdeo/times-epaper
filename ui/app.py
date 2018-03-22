import toga
# from Pillow import Image
from datetime import datetime, timedelta
from toga.style.pack import Pack, COLUMN, ROW


class EPaper(object):
    def __init__(self):
        self.num_pages = 0
        self.publications = ['The Times of India', 'Economic Times']
        self.editions = ['Mumbai', 'Pune', 'Bangalore', 'Hyderabad']
        self.today = datetime.today().date()
        self.available_dates = [(self.today - timedelta(i)).strftime('%Y%m%d')
                                for i in range(1, 8)]
        # Paths of downloaded page thumbnails
        self.thumbnail_image_paths = [None for i in range(self.num_pages)]
        # Array of all thumbnail images loaded in memory
        self.thumbnail_images = [None for i in range(self.num_pages)]
        # Paths of downloaded page images
        self.page_image_paths = [None for i in range(self.num_pages)]
        # store current viewed Image()
        self.current_page = None


class EpaperApp(toga.App):
    def startup(self):
        self.data = self.get_data()
        self._menu_items = {}
        self.document_types = ['.jpg', '.png', '.pdf']
        self.main_window = toga.MainWindow(self.name)

        # Selection widgets
        self.publication_selection = toga.Selection(
            items=self.data.publications,
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )
        self.edition_selection = toga.Selection(
            items=self.data.editions,
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )
        self.date_selection = toga.Selection(
            items=self.data.available_dates,
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )

        print(self.data.num_pages)

        # Thumbnail View Commands
        thumbnail_commands = []
        for i in range(self.data.num_pages):
            thumbnail_commands.append(
                toga.Command(
                    self.display_page(None, i),
                    label='Display Page',
                    tooltip='Display Page {}'.format(i),
                    # icon=self.data.thumbnail_images[i],
                    group=toga.Group.VIEW,
                    section=0
                )
            )

        thumbnail_buttons = [
            toga.Button(
                'Page {}'.format(i),
                on_press=self.display_page(None, i),
                # icon=self.data.thumbnail_images[i],
                style=Pack(
                    width=100,
                    padding=2
                )
            ) for i in range(self.data.num_pages)]

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
                image=self.data.current_page,
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

    def get_data(self):
        """Get data from EPaper object."""
        paper = EPaper()
        paper.num_pages = 50
        return paper


def main():
    return EpaperApp('E-Paper App', 'org.rpdlabs.epaper')


if __name__ == '__main__':
    main().main_loop()
