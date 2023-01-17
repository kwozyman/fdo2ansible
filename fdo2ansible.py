#!/usr/bin/env python3

import logging
import flask
import os
import subprocess
import json
import yaml


class F2AServer():
    def __init__(self, **kwargs):
        self.loglevel = 'debug'
        self.log_format = '%(asctime)19s - %(levelname)8s - %(message)s'
        self.log_datefmt = '%d-%m-%Y %H:%M:%S'
        self.logmap = {
            'info': logging.INFO,
            'warning': logging.WARN,
            'warn': logging.WARN,
            'debug': logging.DEBUG
        }
        final_config = {**self.cmdargs(), **kwargs}
        for k in final_config:
            setattr(self, k, final_config[k])
        self._basic_logging()
        self.set_loglevel(self.loglevel)
        final_config['awx_token'] = '********'
        logging.debug('Using config: {}'.format(final_config))
        self.known_guids = []
        self.webapp = flask.Flask('fdo2ansible')
        self.get_known_guids()
        self.set_endpoints()
        self.webapp.run(host='0.0.0.0', port=5000)
    
    def _basic_logging(self):
        logging.basicConfig(level=self.logmap[self.loglevel],
                            format=self.log_format,
                            datefmt=self.log_datefmt)

    def _build_awx_params(self):
        params = [self.awx, '--conf.host', self.awx_endpoint, '--conf.token', self.awx_token,
                    '--conf.insecure', ' ']
        return ' '.join(params)

    def set_loglevel(self, level):
        logging.getLogger().setLevel(self.logmap[level])
        logging.debug('DEBUG mode is enabled')

    def cmdargs(self):
        """
        Parse command line arguments and read config files (if module exists)
        """
        description = 'Simple facts receiver'
        try:
            import configargparse
            parser = configargparse.ArgParser(
                default_config_files=[
                    'f2aserver.config',
                    '/etc/f2aserver/config',
                    '~/.config/f2aserver/config'],
                description=description
            )
        except ModuleNotFoundError:
            logging.error('Could not find configargparse module')
            exit(1)
            import argparse
            parser = argparse.ArgumentParser(
                description=description
                )

        parser.add_argument('--loglevel', '--log-level',
                            choices=self.logmap.keys(),
                            type=str.lower,
                            default=self.loglevel,
                            help='Logging level',
                            )
        parser.add_argument('--log-format',
                            type=str,
                            default=self.log_format,
                            help='Python Logger() compatible format string')
        parser.add_argument('--log-datefmt',
                            type=str,
                            default=self.log_datefmt,
                            help='Python Logger() compatible date format str')
        parser.add_argument('--owner-tool',
                            type=str,
                            default='/usr/bin/fdo-owner-tool',
                            help='Set path for the fdo-owner-tool binary',
                            env_var='OWNER_TOOL')
        parser.add_argument('--owner-vouchers-dir',
                            type=str,
                            default='/data/owner_onboarding_server/owner_vouchers',
                            help='Path to the owner onboarding server voucher directory',
                            env_var='OWNER_VOUCHERS_DIR')
        parser.add_argument('--awx',
                            type=str,
                            default='/usr/local/bin/awx',
                            help='Path to awx binary')
        parser.add_argument('--awx-endpoint',
                            type=str,
                            help='host of ansible automation platform',
                            env_var='AWX_ENDPOINT')
        parser.add_argument('--awx-token',
                            type=str,
                            help='Access token passed to AWX',
                            env_var='AWX_TOKEN')
        parser.add_argument('--awx-inventory-id',
                            type=int,
                            default=1,
                            help='Inventory id of the used AWX inventory')

        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = False

        try:
            import argcomplete
            from os.path import basename
            parser.add_argument('--bash-completion',
                                action='store_true',
                                help='Dump bash completion file.'
                                ' Activate with eval '
                                '"$({} --bash-completion)"'.format(basename(__file__)))
            argcomplete.autocomplete(parser)
        except ModuleNotFoundError:
            pass

        args = parser.parse_args()
        if 'bash_completion' in args:
            if args.bash_completion:
                print(argcomplete.shellcode(basename(__file__), True, 'bash'))
        return vars(args)

    def get_ansible_hosts(self):
        try:
            host_list_output = subprocess.check_output(self._build_awx_params() + ' host list', shell=True)
            return(json.loads(host_list_output))
        except Exception as e:
            logging.error('Cannot list Ansible hosts')
            logging.error(e)
            return None

    def is_registered(self, guid):
        host_list = self.get_ansible_hosts()
        if host_list is None:
            logging.error('Cannot determine if {} already in Ansible'.format(guid))
            return None
        for host in host_list['results']:
            variables = yaml.safe_load(host['variables'])
            if 'guid' in variables.keys():
                if variables['guid'] == guid:
                    logging.debug('{} is already registered'.format(guid))
                    return True
        logging.debug('{} is not registered'.format(guid))
        return False
    
    def register_to_ansible(self, guid):
        host_vars = {'guid': guid}
        try:
            register_output = subprocess.check_output(self._build_awx_params() + 'host create --name {} --inventory {} --variables "guid: {}"'.format(guid, self.awx_inventory_id, guid), shell=True)
            logging.debug('Registered {} to Ansible: {}'.format(guid, register_output))
            return True
        except:
            logging.debug('Could not register {} to Ansible: {}'.format(guid, register_output))
            return False

    def get_known_guids(self):
        for root, dirs, files in os.walk(self.owner_vouchers_dir):
            for f in files:
                #TODO: regex validation of guid file name
                if f in self.known_guids:
                    logging.debug('{} already known, skipping'.format(guid))
                else:
                    self.known_guids.append(f)
                    logging.info('Found new device {}, added to known list'.format(f))

    def set_endpoints(self):
        @self.webapp.route('/')
        def about_page():
            return('FDO2Ansible')
        
        @self.webapp.route('/device/<guid>')
        def register_device(guid):
            logging.info('Received register request from {}'.format(guid))
            if guid in self.known_guids:
                registered = self.is_registered(guid)
                if registered is None:
                    logging.error('Cannot determine registration for device {}'.format(guid))
                    flask.abort(500)
                if registered:
                    logging.warning('{} is already registered'.format(guid))
                    return('{} registered already\n'.format(guid))
                else:
                    logging.info('Registering {} to Ansible'.format(guid))
                    if not self.register_to_ansible(guid):
                        logging.error('Could not register {} to Ansible!'.format(guid))
                        flask.abort(500)
                    else:
                        logging.info('{} added to Ansible'.format(guid))
                        return('OK')
            else:
                logging.warning('{} not found in known devices'.format(guid))
                flask.abort(404)

if __name__ == '__main__':
    F2AServer()
