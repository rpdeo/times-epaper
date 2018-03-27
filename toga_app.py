import toga
from toga.style.pack import Pack, COLUMN, ROW

from epaper import EPaper, SelectedEPaper


class EpaperApp(toga.App):
    def startup(self):
        # Data object instances
        self.epaper = EPaper()
        self.selected_epaper = SelectedEPaper()

        # GUI
        self._menu_items = {}
        self.document_types = ['.jpg', '.png', '.pdf']
        self.main_window = toga.MainWindow(self.name)

        # Selection widgets
        self.publication_selection = toga.Selection(
            items=self.epaper.publications.keys(),
            style=Pack(
                flex=1,
                padding_left=5,
                padding_right=5
            )
        )
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
        for i in range(self.selected_epaper.num_pages):
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
            ) for i in range(self.selected_epaper.num_pages)
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
                image=self.selected_epaper.get_page_image(
                    self.selected_epaper.current_page),
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
