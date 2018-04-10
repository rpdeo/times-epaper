import sys
import os


def notify(title=None, message=None):
    '''Notify user when download is complete.'''
    if sys.platform == 'darwin':
        command = '''/usr/bin/osascript -e "display notification \\"{0}\\" with title \\"{1}\\"" '''.format(
            message, title)
        # print(command)
        os.system(command)
    elif sys.platform == 'linux':
        command = '''/usr/bin/notify-send -u low "{0}" "{1}" '''.format(
            title, message)
        # print(command)
        os.system(command)
    elif sys.platform == 'windows':
        # This is here to say its possible for win10 with following lib
        # https://github.com/jithurjacob/Windows-10-Toast-Notifications
        # from win10toast import ToastNotifier
        # ToastNotifier().show_toast(title, message, duration=5)
        pass
    else:
        # ignore for others
        pass


def mkdirp(path):
    """Create directory hierarchy, by resolving the absolute path from *path*.
But really use os.makedirs(path, exist_ok=True) rather than this.
"""
    stack = []
    current = os.path.abspath(path)
    while not os.path.isdir(current):
        stack.append(current)
        current = os.path.dirname(current)

    while len(stack) > 0:
        current = stack.pop()
        os.mkdir(current)
