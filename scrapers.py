from itertools import chain
import json
import re
import requests
import sys
from urllib.parse import unquote

from CLIppy import flatten, safe_encode, soup_me


def get_bar(query):
    """
    query -> (barname, bar_url)
    """
    BASE_URL = 'https://www.beermenus.com/{}'
    PARAMS = {'q': safe_encode(query)}

    soup = soup_me(BASE_URL.format('search'), PARAMS)

    try:
        PATTERN = re.compile('^/places/')
        top_hit, *_ = [match for match in soup('h3', class_='mb-0 text-normal')
                       if match('a', href=PATTERN)]
    except:
        print('\ncouldn\'t find that bar...\n')
        sys.exit(0)

    barname = top_hit.a.text
    bar_url = BASE_URL.format(top_hit.a['href'])

    return barname, bar_url


def get_beers(bar_url):
    """
    bar_url -> list of beernames, num on tap (listed 1st)
    """
    soup = soup_me(bar_url, from_headless=True)

    PATTERN = re.compile('^/beers/')
    beers = [li for li in soup('li', class_='pure-list-item')
             if li('a', href=PATTERN)]

    beer_names = [beer.a.text for beer in beers]

    beer_infos = [
        (beer.find('p', class_='caption text-gray mb-0').text
             .strip().split('·'))
        for beer in beers
    ]

    beer_servinginfos = [
        [p.text.strip().split() for p in
         beer('p', class_='caption text-right mb-0')]
        for beer in beers
    ]

    def make_tuple(lst, n):
        """ fill in missing info, and strip extraneous spaces
        """
        lst = list(lst) + [''] * n               # pad with fallback if missing
        return tuple(_.strip() for _ in lst)[:n] # filter to n-tuple

    # TODO when info missing, detect abv ([0-9]%) and use to calibrate rest ?
    KEYS_INFO = ('style', 'abv', 'where') #, 'serving')
    KEYS_SERVINGINFO = ('volume', 'type', 'price')

    # beerstyle, abv, beerplace
    beer_infos = [make_tuple(info, len(KEYS_INFO)) for info in beer_infos]
    # volume, servingtype, price
    beer_servinginfos = [[make_tuple(info, len(KEYS_SERVINGINFO))
                          for info in filter(None, infos)]
                         for infos in beer_servinginfos]

    d_stats = {
        beername: dict(zip(chain(KEYS_INFO, ('serving',)),
                           chain(info, ([dict(zip(KEYS_SERVINGINFO,
                                                  servinginfo))
                                         for servinginfo in servinginfos],))))
        for beername, info, servinginfos in
        zip(beer_names, beer_infos, beer_servinginfos)
    }
    return d_stats


# TODO wrapper to grab key from SECRETS ?
def get_reviews_ratebeer(query, beerpage=None, verbose=False):
    """ Get beer stats

    :query: query beername str
    """
    if verbose:
        print('ratebeer...')

    BASE_URL_API = 'https://beta.ratebeer.com/v1/api/graphql/'

    FIELDS = [
        # 'id',
        'name',
        'averageRating',
        'abv',
        # 'overallScore',
        'description',
        # 'ratingCount'
    ]

    UNRATED = '0.00'
    UNABVED = None

    data = {
        'query': 'query beerSearch($query: String, $order: SearchOrder, $first: Int, $after: ID) { searchResultsArr: beerSearch(query: $query, order: $order, first: $first, after: $after) { totalCount last items { beer { %s __typename } review { id score __typename } __typename   }   __typename } }' % (' '.join(FIELDS)),
        'variables': {'query': query, 'order': 'MATCH', 'first': 20},
        'operationName': 'beerSearch'
    }
    d_hits = (
        requests
        .post(BASE_URL_API,
              data=json.dumps(data),
              headers={'content-type': 'application/json'})
        .json()['data']['searchResultsArr']
    )

    if d_hits['totalCount'] == 0: # no match found
        return {}

    top_hit = d_hits['items'][0]['beer']

    # mean rating = "?.xx" / 5
    try:
        rating = '{:.2f}'.format(top_hit['averageRating'])
    except(TypeError): # None
        rating = UNRATED

    # abv = "?%"
    try:
        abv = '{:.2f}%'.format(top_hit['abv'])
    except(TypeError): # None
        abv = UNABVED

    # TODO ?
    # style
    # where

    # description
    description = top_hit['description']

    beer_stats = {
        # 'abv': abv,
        'description': description
        # 'style': style,
        # 'where': where,
    }
    if rating != UNRATED:
        beer_stats['rating'] = rating
    if abv != UNABVED:
        beer_stats['abv'] = abv

    return beer_stats


def get_reviews_untappd(query, beerpage=None, verbose=False):
    """ Get beer stats

    :query: query beername str
    """
    if verbose:
        print('untappd...')

    BASE_URL = 'https://untappd.com/{}'

    UNRATED = 'N/A'
    UNABVED = 'No'

    def get_beerpage(query):
        """
        :query: beername query str
        :returns: (name, id)
        """
        PARAMS = {'q': safe_encode(query)}

        soup = soup_me(BASE_URL.format('search'), PARAMS)

        top_hit = soup.find('p', class_='name')

        return BASE_URL.format(top_hit.a['href'])

    try:
        beerpage = beerpage if beerpage is not None else get_beerpage(query)
    except(AttributeError): # not found
        return {}

    soup = soup_me(beerpage)

    # mean rating = "?" / 5 #"?/5.0"
    try:
        rating = re.sub('[\(\)]', '',soup.find('span', class_='num').text)
    except(AttributeError): # no match
        assert soup.find('p', class_='info'), "oops - your IP's been blocked. skipping..."
        return {}

    # abv = "?%"
    abv = re.sub(' ABV$', '', soup.find('p', class_='abv').text.strip())

    # style
    style = soup.find('p', class_='style').text

    # TODO ?
    # where

    # long desc
    try:
        description = re.sub(re.compile(' ?Show Less$'), '', soup.find(
            'div', class_="beer-descrption-read-less").text.strip())
    except(AttributeError): # no match
        description = ''

    beer_stats = {
        # 'abv': abv,
        'style': style,
        # 'where': where,
        'description': description
    }
    if rating != UNRATED:
        beer_stats['rating'] = rating
    if abv != UNABVED:
        beer_stats['abv'] = abv

    return beer_stats


def get_reviews_beeradvocate(query, beerpage=None, verbose=False):
    """ Get beer stats

    :query: query beername str
    """
    if verbose:
        print('beeradvocate...')

    BASE_URL = 'https://www.beeradvocate.com/{}'

    UNRATED = '0'
    UNABVED = None

    def get_beerpage(query):
        """
        :query: beername query str
        :returns: (name, id)
        """
        PARAMS = {'q': safe_encode(query),
                  'qt': 'beer'}

        soup = soup_me(BASE_URL.format('search/'), PARAMS)

        try: # redirected directly to beerpage
            relative_url = re.match('^/beer/profile/', soup.find(
                'input', attrs={'name': 'redirect'})['value']).string
        except:
            top_hit = soup.find('a', href=re.compile("^/beer/profile/"))
            relative_url = top_hit['href']

        return BASE_URL.format(relative_url)

    queried = beerpage is None

    try:
        beerpage = beerpage if beerpage is not None else get_beerpage(query)
    except(TypeError): # no hits
        return {}

    soup = soup_me(beerpage)

    try:
        assert 'beers' in {s.text.lower() for s in soup('span', itemprop='title')}
    except(AssertionError): # i.e. place page rather than beer page
        return (get_reviews_beeradvocate(query, verbose=verbose)
                if not queried else {}) # if already tried querying beeradvocate, just leave

    # mean rating = "?" / 5 # "?/5.0"
    rating = soup.find('span', class_='ba-ravg').text

    stats = soup('dd', class_='beerstats')

    # abv = "?%"
    try:
        abv, = [s.text.strip() for s in stats if s.find(
            'span', title='Percentage of alcohol by volume.')]
    except(ValueError): # not reported
        abv = UNABVED

    # style
    PATTERN = re.compile('^/beer/styles')
    style, = [s.text.strip() for s in stats if s.find('a', href=PATTERN)]

    # where = "state, country"
    PATTERN = re.compile('^/place/directory')
    where, = [s.text.strip() for s in stats if s.find('a', href=PATTERN)]

    beer_stats = {
        # 'abv': abv,
        'style': style,
        'where': where
    }
    if rating != UNRATED:
        beer_stats['rating'] = rating
    if abv != UNABVED:
        beer_stats['abv'] = abv

    return beer_stats


def get_beerpages_en_masse(query):
    """Get beer pages via google search

    :returns: {site: beer_url} for subset of sites found
    """

    D_SITES = dict(
        untappd = 'https://untappd.com/b/',
        ratebeer = 'https://www.ratebeer.com/beer/',
        beeradvocate = 'https://www.beeradvocate.com/beer/'
    )

    BASE_URL = 'https://www.google.com/search'
    PARAMS = {'q': safe_encode(query)}

    soup = soup_me(BASE_URL, PARAMS)

    extract_url = lambda site: re.sub('\/url\?q=([^&]*)&.*', '\\1', soup.find(
        'a', href=re.compile('^/url\?q={}'.format(site)))['href'])

    D_URLS ={}
    for k, v in D_SITES.items():
        try:
            D_URLS[k] = unquote(extract_url(v)) # fix % encoding
        except(TypeError): # not found
            pass

    # return {k: extract_url(v) for k,v in D_SITES.items()}
    return D_URLS
