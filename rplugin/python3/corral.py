# encoding: utf-8

"""
                                         888
Presenting…                              888
                                         888
 .d8888b .d88b.  888d888 888d888 8888b.  888
d88P"   d88""88b 888"    888"        "8b 888
888     88    88 888     888    .d888888 888
Y88b.   Y88..88P 888     888    88    88 888
 "Y8888P "Y88P"  888     888    "Y888888 888

A neovim plugin to keep you within your boundaries.
"""

import contextlib
import os
from subprocess import check_output, CalledProcessError

import neovim as nv

# Patch in a helper for getting command output without printing to
# the status line.
def _query(self, command):
    return self.command_output('silent {}'.format(command)).strip()

nv.Nvim.command_query = _query

# And another for getting the working directory, with a trailing slash so it
# plays nice with `os.path.dirname`.
@property
def _cwd(self):
    return self._session.command_query('pwd') + '/'

nv.api.nvim.Current.directory = _cwd


class NoRepoError(Exception):
    """
    The working directory is not in a repository, making the current operation
    invalid.
    """
    pass


@nv.plugin
class Corral(object):
    """
    The thing what does the stuff
    """
    def __init__(self, nvim):
        self.nvim = nvim

        self.options = {
            'enabled_vcs': ['git', 'svn'],
            'vcs_command': {
                'git': 'git rev-parse --show-toplevel',
                'svn': 'svn info --show-item wc-root',
            },
            'truncate': True, # Whether to truncate messages to fit the window.
            'noisy': True, # Whether `echo_info` is enabled.
        }

        self.current_vcs = None
        self.current_repo = None
        self.enabled = False

    #
    # Events
    #

    @nv.rpc_export('corral_check')
    def check_buffer(self, buffer_number):
        """
        Corral the current buffer if conditions are right.
        """
        if not self.enabled:
            return

        buf = self.nvim.buffers[int(buffer_number)]

        # Ignore buffers that aren't files.
        if buf.options['buftype']:
            return

        try:
            if not self.is_in_current_repo(buf.name):
                buf.options['readonly'] = True
                buf.options['modifiable'] = False
                buf.vars['corralled'] = True

                if buf == self.nvim.current.buffer:
                    self.echo_warn(
                        "Outside of repository; modification disabled"
                    )

            elif buf.vars.get('corralled'):
                buf.options['readonly'] = False
                buf.options['modifiable'] = True
                del buf.vars['corralled']

                if buf == self.nvim.current.buffer:
                    self.echo_info("No longer outside of repository")

        except NoRepoError:
            pass

    @nv.rpc_export('corral_cwd_changed')
    def cwd_changed(self):
        """
        Update whether corral is active based on whether the new working
        directory is a repository.
        """
        new_vcs, new_repo = self.discover_vcs(self.nvim.current.directory)
        if not new_repo == self.current_repo:
            if new_repo:
                self.echo_info(
                    "Corralling new buffers to {} repository at '{}'"
                    .format(new_vcs, new_repo)
                )
            else:
                self.echo_info("No longer in a repository")

        self.current_vcs = new_vcs
        self.current_repo = new_repo

    #
    # Commands
    #

    @nv.command('CorralEnable')
    def enable(self):
        """
        Start corralling new buffers. Does not change existing buffers.
        """
        if self.enabled:
            return

        # We can't do this during init, so do it on enable. It doesn't hurt
        # to recreate them.
        self.nvim.command('augroup corral | autocmd! | augroup END')
        self.nvim.command(
            'augroup corral | '
            'au BufReadPre * call rpcnotify({0}, "corral_check", bufnr("%")) | '
            'au DirChanged * call rpcnotify({0}, "corral_cwd_changed") | '
            'augroup END'
            .format(self.nvim.channel_id)
        )

        self.enabled = True
        self.cwd_changed()

    @nv.command('CorralDisable')
    def disable(self):
        """
        Stop corralling buffers. Does not undo changes to existing buffers.
        """
        self.enabled = False

    @nv.command('CorralToggle')
    def toggle(self):
        """
        Invert the enabled state. Good for use with :map.
        """
        self.enabled = not self.enabled

    #
    # VCS helpers
    #

    def discover_vcs(self, path):
        """
        Determine if `path` is in a repo of any `enabled_vcs`. If so, return
        both the VCS type and the root of the repository.
        """
        for vcs in self.options['enabled_vcs']:
            repo = self.repo_root(path, vcs)
            if repo:
                return vcs, repo

        return None, None

    def is_in_current_repo(self, path):
        """
        Whether `path` is within the same repository as the working directory.
        """
        if not self.current_vcs:
            raise NoRepoError()

        current_repo = self.repo_root(self.nvim.current.directory, self.current_vcs)
        if not current_repo:
            raise NoRepoError(path)

        return current_repo == self.repo_root(path, self.current_vcs)

    def repo_root(self, path, vcs):
        """
        Get the root of the `vcs` repository that `path` exists within, if one.
        """
        with working_directory(os.path.dirname(path)):
            try:
                return check_output(
                    self.options['vcs_command'][vcs],
                    universal_newlines=True,
                    shell=True
                ).strip()
            except CalledProcessError:
                return None

    #
    # Logging
    #

    def echo_hl(self, message, hl):
        message = "corral: {}".format(message)

        # Truncate the message to the width of the window so we never cause the
        # 'Press ENTER' prompt.
        cols = self.nvim.current.window.width
        if self.options['truncate'] and len(message) > cols - 1:
            message = message[:cols - 2] + '…'

        self.nvim.command(
            'silent echohl {} | echo "{}" | silent echohl None'
            .format(hl, message)
        )

    def echo_info(self, message):
        if self.options['noisy']:
            self.echo_hl(message, 'None')

    def echo_warn(self, message):
        self.echo_hl(message, 'WarningMsg')

    def echo_error(self, message):
        self.echo_hl(message, 'ErrorMsg')


@contextlib.contextmanager
def working_directory(path):
    """
    Execute some code in a different working directory.
    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)
