import configparser
import logging
import os

import epaper

# logging
logger = logging.getLogger('epaper')


class AppConfig:
    def __init__(self):
        self.config_home = os.path.join(
            os.environ.get('HOME'),
            '.config',
            'epaper-app'
        )

        self.config_file = os.path.join(
            self.config_home,
            'config.ini'
        )

        self.cache_dir = os.path.join(
            os.environ.get('HOME'),
            '.cache',
            'epaper-app'
        )

        self.valid = False

        self.config = configparser.ConfigParser()

        if not os.path.exists(self.config_home):
            os.makedirs(self.config_home)

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            self.validate_config()

        # if no config file found or config read was not valid, create new
        # default config, and save it.
        if not os.path.exists(self.config_file) or \
           not self.valid:
            self.config['App'] = {
                'app_name': 'EPaperApp',
                'app_version': epaper.__version__,
                'cache_dir': self.cache_dir,
                'log_file': os.path.join(self.cache_dir, 'epaper-app.log')
            }
            self.config['Http'] = {
                'request_delay_min': 15,
                'request_delay_max': 30,
                'user_agent': '/'.join([self.config['App']['app_name'],
                                        self.config['App']['app_version']
                                        ]),
            }
            self.config['Publishers'] = {
                'TOI': ''
            }
            self.config['TOI'] = {
                'site_url': 'https://epaperlive.timesgroup.com',
                'site_archive_url': 'https://epaperlive.timesgroup.com/Search/Archives',
                'selected_pub_code': '',
                'selected_edition_code': ''
            }
            self.save()
        else:
            # update config to match software state if loaded from
            # self.config_file
            self.update_config()

    def validate_config(self):
        self.valid = False
        sections = self.config.sections()
        if not sections:
            return
        # damn this is hacky
        a_publisher = ([
            publisher for publisher in self.config['Publishers']][0]).upper()
        # These sections must be present
        if 'App' in sections and \
           'Http' in sections and \
           'Publishers' in sections and \
           a_publisher in sections and \
           self.config['App']['cache_dir'] and \
           self.config['Http']['request_delay_min'] and \
           self.config['Http']['request_delay_max'] and \
           self.config[a_publisher]['site_url'] and \
           self.config[a_publisher]['site_archive_url']:
            self.valid = True

    def save(self):
        '''Validate and save config to config_file.'''
        self.validate_config()
        if self.valid:
            with open(self.config_file, 'w') as fd:
                self.config.write(fd)

    def update_config(self):
        '''Update saved config for newer values of certain configuration variables.'''
        # update app_version
        self.config['App']['app_version'] = epaper.__version__
        # update user_agent
        self.config['Http']['user_agent'] = self.config['App']['app_name'] + '/' + \
            self.config['App']['app_version']
        # save config
        self.save()
