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
        top_hit, *_ = [match for match in soup('h3', class_='mb-0 text-normal')
                       if match('a', href=re.compile('^/places/'))]
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
    soup = soup_me(bar_url)

    beers = soup('a', href=re.compile('^/beers/'))

    beer_names = [beer.text for beer in beers
                  if beer.text != 'more'] # extra beer link

    beer_infos = [info.text.split('\n') for info in
                  soup('p', class_='caption text-gray mb-0')]

    beer_servinginfos = [info.text.split('\n') for info in
                         soup('p', class_='caption text-right mb-0 last')]

    for beer_data in (beer_infos, beer_servinginfos):
        assert len(beer_names) == len(beer_data), '{} != {}'.format(
            len(beer_names), len(beer_data))

    def get_info(idx, infolst):
        try:
            info = infolst[idx].strip()
        except(IndexError):
            info = ''
        return info

    beer_infos = [tuple(get_info(i, info) for i in (1,3,5)) # beerstyle, abv, beerplace
                  for info in beer_infos]
    beer_servinginfos = [tuple(flatten(get_info(i, info).lower().split(' ')
                                       for i in (1,2))) # volume, servingtype, price
                         for info in beer_servinginfos]

    KEYS_INFO = ('style', 'abv', 'where')#, 'serving')
    KEYS_SERVINGINFO = ('volume', 'type', 'price')

    to_dict = lambda ks, vs: {k: v for k,v in zip(ks,vs) if v is not ''}

    d_stats = {
        beername: to_dict(
            chain(KEYS_INFO, ('serving',)),
            chain(info, ([],))
        ) for beername, info in zip(beer_names, beer_infos)
    }
    for beername, servinginfo in zip(beer_names, beer_servinginfos):
        d_stats[beername]['serving'].append(to_dict(KEYS_SERVINGINFO, servinginfo))

    return d_stats


# TODO wrapper to grab key from SECRETS ?
def get_reviews_ratebeer(query, beerpage=None):
    """ Get beer stats

    :query: query beername str
    """
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


    data = {
        'query': 'query beerSearch($query: String, $order: SearchOrder, $first: Int, $after: ID) { searchResultsArr: beerSearch(query: $query, order: $order, first: $first, after: $after) { totalCount last items { beer { %s __typename } review { id score __typename } __typename   }   __typename } }' % (' '.join(FIELDS)),
        'variables': {'query': query, 'order': 'MATCH', ' first': 20},
        'operationName':'beerSearch'
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
    rating = '{:.2f}'.format(top_hit['averageRating'])

    # abv = "?%"
    abv = '{:.2f}%'.format(top_hit['abv'])

    # style

    # where

    # description
    description = top_hit['description']


    # BASE_URL = 'https://www.ratebeer.com/beer/{}/{}/'

    # def get_beerpage(query):
    #     """
    #     :query: beername query str
    #     :returns: (name, id)
    #     """
    #     BASE_URL_API = 'https://beta.ratebeer.com/v1/api/graphql/'

    #     data = {
    #         "query": "query beerSearch($query: String, $order: SearchOrder, $first: Int, $after: ID) { searchResultsArr: beerSearch(query: $query, order: $order, first: $first, after: $after) { totalCount last items { beer { id name overallScore ratingCount __typename } review { id score __typename } __typename   }   __typename } }",
    #         "variables": {"query": query, "order": "MATCH", " first": 20},
    #         "operationName":"beerSearch"
    #     }
    #     d_hits = (
    #         requests
    #         .post(BASE_URL_API,
    #             data=json.dumps(data),
    #             headers={"content-type": "application/json"})
    #         .json()['data']['searchResultsArr']
    #     )

    #     if d_hits['totalCount'] == 0: # no match found
    #         raise Exception

    #     top_hit = d_hits['items'][0]['beer']

    #     # beername = top_hit['name']
    #     # beer_id = top_hit['id']

    #     return BASE_URL.format(safe_encode(
    #         top_hit['name'], pattern='[^\w\n]+', space_char='-'),
    #         top_hit['id'])

    # # get stats
    # try:
    #     beerpage = beerpage if beerpage is not None else get_beerpage(query)
    # except(Exception): # not found
    #     return {}

    # soup = soup_me(beerpage)

    # # mean rating = "?" / 5 #"?/5.0"
    # rating = re.sub('\/5\.?0?$', '', soup.find('a', attrs={'name': 'real average'}).strong.text)

    # # abv = "?%"
    # abv = soup.find('abbr', title='Alcohol By Volume').next.next.next.strong.text

    # # style
    # style, = (tag.text for tag in soup('a', href=re.compile("^/beerstyles/"))
    #           if tag.previous == 'Style: ')

    # where

    beer_stats = {
        'rating': rating,
        'abv': abv,
        'description': description
        # 'style': style,
        # 'where': where,
    }

    return beer_stats


def get_reviews_untappd(query, beerpage=None):
    """ Get beer stats

    :query: query beername str
    """
    BASE_URL = 'https://untappd.com/{}'

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
    rating = re.sub('[\(\)]', '',soup.find('span', class_='num').text)

    # abv = "?%"
    abv = re.sub(' ABV$', '', soup.find('p', class_='abv').text.strip())

    # style
    style = soup.find('p', class_='style').text

    # where

    # long desc
    description = re.sub(re.compile(' ?Show Less$'), '', soup.find(
        'div', class_="beer-descrption-read-less").text.strip())

    beer_stats = {
        'abv': abv,
        'style': style,
        # 'where': where,
        'description': description
    }
    if rating != 'N/A': # not rated
        beer_stats['rating'] = rating

    return beer_stats


def get_reviews_beeradvocate(query, beerpage=None):
    """ Get beer stats

    :query: query beername str
    """
    BASE_URL = 'https://www.beeradvocate.com/{}'

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

    try:
        beerpage = beerpage if beerpage is not None else get_beerpage(query)
    except(TypeError): # no hits
        return {}

    soup = soup_me(beerpage)

    try:
        assert soup.find('div', id='info_box').find('b').text == 'BEER INFO'
    except(AssertionError): # e.g. google found place page
        return get_reviews_beeradvocate(query) if beerpage else {}

    # mean rating = "?" / 5 #"?/5.0"
    rating = soup.find('span', class_='ba-ravg').text
    # rating = '' if rating == '0' else rating # i.e. not rated

    # abv = "?%"
    abv = soup.find('b', text='Alcohol by volume (ABV):').next.next.strip()

    # style
    style = soup.find('b', text='Style:').next.next.next.text

    # where = "state, country"
    where = ', '.join(tag.text for tag in soup('a', href=re.compile(
        '^/place/directory/.')))

    beer_stats = {
        'abv': abv,
        'style': style,
        'where': where
    }
    if rating != '0': # not rated
        beer_stats['rating'] = rating

    return beer_stats


def get_beerpages_en_masse(query):
    """Get beer pages via google search

    :returns: {site: beer_url} for subset of sites found
    """

    D_SITES = {
        'untappd': 'https://untappd.com/b/',
        'ratebeer': 'https://www.ratebeer.com/beer/',
        'beeradvocate': 'https://www.beeradvocate.com/beer/'
    }

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
