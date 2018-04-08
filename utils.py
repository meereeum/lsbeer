import re
import requests

from bs4 import BeautifulSoup


def safe_encode(*args, pattern=' ', space_char='+'):
    """default: replace spaces with '+'
    """
    # SPACE_CHAR = '+'
    # return SPACE_CHAR.join(args).replace(' ', SPACE_CHAR)
    return re.sub(re.compile(pattern),
                  space_char,
                  space_char.join(args),
                  re.DOTALL)


def soup_me(*args, verbose=False, **kwargs):
    DEFAULT = {'headers': {'User-agent': 'shiffy47'}}
    kwargs = {**DEFAULT, **kwargs}

    # return BeautifulSoup(requests.get(*args, **kwargs).content, 'lxml')

    if verbose:
        print('pinging...')
        print(args)
        print(kwargs)

    requested = requests.get(*args, **kwargs)
    requested.encoding = 'base64' # fix Petite Sour Rosé
    soup = BeautifulSoup(requested.text, 'lxml')
    # soup = BeautifulSoup(requests.get(*args, **kwargs).content, 'lxml')

    if verbose:
        print('...&done')

    return soup
