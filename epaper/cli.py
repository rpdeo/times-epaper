from datetime import datetime
from epaper.appconfig import AppConfig
from epaper.epaper import EPaper
from epaper.scraper import Scraper
from epaper.ui import UI
import click
import epaper
import json
import logging
import os

logger = logging.getLogger('cli')


def doit(interactive=True,
         publication_code=None,
         edition_code=None,
         date=None,
         from_config=False):  # noqa: we know this function is complex
    '''Main Execution Module'''
    # Load app configuration: app-specific configuration management
    app_config = AppConfig()

    # setup logging
    logging.basicConfig(
        filename=app_config.config['App']['log_file'],
        filemode='w',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )

    # choose a default publisher -- as of now this is the only one.
    publisher = 'TOI'

    # Scraper instance: scraper functions
    scraper = Scraper(publisher=publisher, app_config=app_config)

    # UI instance: generic ui interaction functions
    ui = UI(publisher=publisher, app_config=app_config, text=True)

    # Data instance: Data management
    epaper = EPaper(publisher=publisher, app_config=app_config)

    # Pick a publication
    doc = scraper.fetch(scraper.site_archive_url)

    # Highlight if not available
    message = 'This website is currently not available in your region.'
    if doc and (message in doc.body.text):
        logger.error(message)
        print(message)
        return False

    if doc:
        epaper.publications = scraper.parse_publication_codes(doc)
        if publication_code and \
           (publication_code in epaper.publications.values()):
            # non-interactive with cli options
            epaper.selected_publication = [
                (k, v) for k, v in epaper.publications.items() if v == publication_code][0]
        elif publication_code is None and from_config:
            # non-interactive with config file
            publication_code = app_config.config[publisher].get(
                'selected_pub_code', None)
            if publication_code in epaper.publications.values():
                epaper.selected_publication = [
                    (k, v) for k, v in epaper.publications.items() if v == publication_code][0]
        else:
            # simple interactive mode
            epaper.selected_publication = ui.select_publication(
                epaper.publications,
                default=app_config.config[publisher].get(
                    'selected_pub_code', None)
            )
    else:
        logger.error('Could not obtain publication codes.')
        return False

    # Pick an edition
    doc = scraper.fetch(
        scraper.site_archive_edition_url.format(
            pub_code=epaper.selected_publication[1]))

    if doc:
        epaper.editions = scraper.parse_edition_codes(doc)
        if edition_code and \
           (edition_code in epaper.editions.values()):
            # non-interactive with cli options
            epaper.selected_edition = [
                (k, v) for k, v in epaper.editions.items() if v == edition_code][0]
        elif edition_code is None and from_config:
            # non-interactive with config file
            edition_code = app_config.config[publisher].get(
                'selected_edition_code', None)
            if edition_code in epaper.editions.values():
                epaper.selected_edition = [
                    (k, v) for k, v in epaper.editions.items() if v == edition_code][0]
        else:
            # simple interactive mode
            epaper.selected_edition = ui.select_edition(
                epaper.editions,
                default=app_config.config[publisher].get(
                    'selected_edition_code', None)
            )
    else:
        logger.error('Could not obtain edition codes.')
        return False

    if epaper.selected_publication[1] == '' or \
       epaper.selected_edition[1] == '':
        return False

    epaper.save_codes_to_config()

    # Pick a date, if we are in interactive mode, else it defaults to todays date.
    # XXX: date may not be required for some editions...
    if interactive:
        epaper.selected_date = ui.select_pub_date()
    elif isinstance(date, type('')):
        epaper.selected_date = datetime.strptime(date, '%Y-%m-%d')

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


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--interactive', default=True, is_flag=True, help='Run in interactive mode.')
@click.option('--publication_code', default='', help='Publication code as on SITE_ARCHIVE')
@click.option('--edition_code', default='', help='Edition code as on SITE_ARCHIVE')
@click.option('--date', default=str(datetime.now().date()), help='Edition date, default is todays date.')
@click.option('--from_config', default=False, is_flag=True, help='Use publication and edition codes from default config file.')
@click.option('--verbose', default=False, is_flag=True, help='Be more verbose on STDOUT.')
@click.option('--version', is_flag=True, help='Print version.')
def main(interactive,
         publication_code,
         edition_code,
         date,
         from_config,
         verbose,
         version):
    '''EPaper Command Line Interface.'''

    if version:
        click.echo('EPaper version {0}'.format(epaper.__version__))
    elif publication_code and \
            edition_code and \
            date:
        if verbose:
            click.echo('Non-interactive mode.')
        return doit(interactive=False,
                    publication_code=publication_code,
                    edition_code=edition_code,
                    date=date,
                    from_config=False)
    elif from_config:
        if verbose:
            click.echo('Using configured settings.')
        return doit(interactive=False, from_config=True)
    elif interactive:
        if verbose:
            click.echo('Using interactive mode.')
        return doit(interactive=True, from_config=False)
    else:
        click.echo('You have selected an unknown cli configuration. Try again!')
        return False


if __name__ == '__main__':
    main()
