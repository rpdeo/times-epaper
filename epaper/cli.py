from epaper.appconfig import AppConfig
from epaper.epaper import EPaper
from epaper.scraper import Scraper
from epaper.ui import UI
import click
import json
import logging
import os

logger = logging.getLogger('cli')


@click.command()
@click.option('--publication_code', default='TOI', help='Publication code as on SITE_ARCHIVE')
@click.option('--edition_code', default='BOM', help='Edition code as on SITE_ARCHIVE')
def main(publication_code, edition_code):  # noqa: ok we know this is complex
    '''EPaper Command Line Interface.'''
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


if __name__ == '__main__':
    main()
