import argparse
from collections import defaultdict
import itertools
import json
import re
import requests
import sys
from urllib.parse import unquote

from CLIppy import flatten, safe_encode, soup_me

from CLIppy import flatten, get_from_file, safe_encode, soup_me

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
    bar_url -> list of beernames
    """
    soup = soup_me(bar_url)

    beers = soup('a', href=re.compile('^/beers/'))

    beer_names = [beer.text for beer in beers]

    # get_beer_info = lambda tag: tag.next.next.next.next.text.replace(
    #     '\n','').split('·')

    # beer_types, beer_abvs, beer_places = (
    #     list(_) for _ in itertools.zip_longest(
    #         *(tuple(info.strip() for info in get_beer_info(beer))
    #           for beer in beers), fillvalue=''))
    # TODO

    return beer_names


def get_beers_from_file(f):
    """
    path/to/file -> list of beernames
    """
    return get_from_file(f=f)


# TODO wrapper to grab key from SECRETS ?
def get_reviews_ratebeer(query, beerpage=None):
    """ Get beer stats

    :query: query beername str
    """
    BASE_URL = 'https://www.ratebeer.com/beer/{}/{}/'

    def get_beerpage(query):
        """
        :query: beername query str
        :returns: (name, id)
        """
        BASE_URL_API = 'https://beta.ratebeer.com/v1/api/graphql/'

        data = {
            "query": "query beerSearch($query: String, $order: SearchOrder, $first: Int, $after: ID) { searchResultsArr: beerSearch(query: $query, order: $order, first: $first, after: $after) { totalCount last items { beer { id name overallScore ratingCount __typename } review { id score __typename } __typename   }   __typename } }",
            "variables": {"query": query, "order": "MATCH", " first": 20},
            "operationName":"beerSearch"
        }
        d_hits = (
            requests
            .post(BASE_URL_API,
                data=json.dumps(data),
                headers={"content-type": "application/json"})
            .json()['data']['searchResultsArr']
        )

        if d_hits['totalCount'] == 0: # no match found
            raise Exception

        top_hit = d_hits['items'][0]['beer']

        # beername = top_hit['name']
        # beer_id = top_hit['id']

        return BASE_URL.format(safe_encode(
            top_hit['name'], pattern='[^\w\n]+', space_char='-'),
            top_hit['id'])

    # get stats
    try:
        beerpage = beerpage if beerpage is not None else get_beerpage(query)
    except(Exception): # not found
        return {}

    soup = soup_me(beerpage)

    # mean rating = "?" / 5 #"?/5.0"
    rating = re.sub('\/5\.?0?$', '', soup.find('a', attrs={'name': 'real average'}).strong.text)

    # abv = "?%"
    abv = soup.find('abbr', title='Alcohol By Volume').next.next.next.strong.text

    # style
    style, = (tag.text for tag in soup('a', href=re.compile("^/beerstyles/"))
              if tag.previous == 'Style: ')

    # where

    beer_stats = {
        'rating': rating,
        'abv': abv,
        'style': style#,
        # 'where': where,
    }

    return beer_stats
    # return rating, beer_stats


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
        'rating': rating,
        'abv': abv,
        'style': style,
        # 'where': where,
        'description': description
    }

    # return rating, beer_stats
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

    # mean rating = "?" / 5 #"?/5.0"
    rating = soup.find('span', class_='ba-ravg').text

    # abv = "?%"
    abv = soup.find('b', text='Alcohol by volume (ABV):').next.next.strip()

    # style
    style = soup.find('b', text='Style:').next.next.next.text

    # where = "state, country"
    where = ', '.join(tag.text for tag in soup('a', href=re.compile(
        '^/place/directory/.')))

    beer_stats = {
        'rating': rating,
        'abv': abv,
        'style': style,
        'where': where
    }

    # return rating, beer_stats
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


# def get_beerpages(query):

#     D_URLS = {
#         'untappd': get_reviews_untappd,
#         'ratebeer': get_reviews_ratebeer,
#         'beeradvocate': get_reviews_beeradvocate
#     }

#     return D_URLS


def alternate_main(barquery=None, beerfile=None, fancy=False, sorted_=False, verbose=False):

    D_ACTIONS = {
        'untappd': get_reviews_untappd,
        'ratebeer': get_reviews_ratebeer,
        'beeradvocate': get_reviews_beeradvocate
    }

    if barquery:
        barname, bar_url = get_bar(barquery)
        beerlst = get_beers(bar_url)
    else:
        barname = beerfile.split('_')[-1]
        beerlst = get_beers_from_file(beerfile)

        D_URLS = get_beerpages_en_masse(beer)

        # for site, url in get_beerpages_en_masse(beer).items():
            # rating, beer_stats = D_ACTIONS[site](beer, beerpage=url)

        # d_reviews = {}
        # d_stats_consensus = defaultdict(lambda: [])

        # dictionary of stats dictionaries
        d_stats = {
            site: action(beer, beerpage=D_URLS.get(
                site, None)) # fallback is beerpage-specific search
            for site, action in D_ACTIONS.items()
        }

        if not d_stats: # no reviews found
            print('\nskipping {}...\n'.format(beer))
            continue

        d_reviews = {k: v['rating'] for k,v in d_stats.items()
                     if v} # skip empty / not found

        # take consensus
        # d_stats_squashed = {}

        PATTERN = '~*~'
        SPACER = '  '
        SEP = '|'

        # header
        print('\n{pattern} {} {pattern} ({}, {})\n'.format(beer,
                                                           d_stats['untappd']['style'],
                                                           d_stats['untappd']['abv'],
                                                           pattern=PATTERN))

        # reviews
        sitetxt = ''.join(
            ('{spacer}',
             '{spacer}{sep}{spacer}'.join(['({})'] * len(d_reviews)),
             '{spacer}')).format(*d_reviews.keys(), spacer=SPACER, sep=SEP)
        # sitetxt = '{spacer}({}){spacer}{sep}{spacer}({}){spacer}{sep}{spacer}({}){spacer}'.format(*d_reviews.keys(), spacer=SPACER, sep=SEP)

        widths = (len(_) for _ in sitetxt.split(SEP))

        reviewtxt = '{sep}'.join(['{:^{}}'] * len(d_reviews)).format(
            *flatten(zip(d_reviews.values(), widths)), sep=SEP)
        # reviewtxt = '{:^{}}{sep}{:^{}}{sep}{:^{}}'.format(
        #     *flatten(zip(d_reviews.values(), widths)), sep=SEP)

        print('\n'.join((reviewtxt, sitetxt)))
        print('')
        # for site, action in D_ACTIONS.items():
        #     url = D_URLS.get(site, None) # fallback is beerpage-specific search
        #     # rating, beer_stats = action(beer, beerpage=url)
        #     beer_stats = action(beer, beerpage=url)
        #     # print('{}: {}'.format(site, beer_stats['rating']))
        #     # if beer_stats:
        #     #     print('{}:'.format(site))
        #     #     print(beer_stats)
        #     d_stats_consensus[site]
        #     d_reviews[site] = beer_stats['rating']

            # beerlines += ['{}: {}'.format(site, rating), beer_stats, '']

    # print(''); pprint_header_with_lines(header, beerlines); print('')


def main(barquery):

    D_ACTIONS = {
        'untappd': get_reviews_untappd,
        'ratebeer': get_reviews_ratebeer,
        'beeradvocate': get_reviews_beeradvocate
    }

    barname, bar_url = get_bar(barquery)
    beerlst = get_beers(bar_url)

    print('__{}__'.format(barname).upper())

    for beer in beerlst:
        print(beer)
        for site, action in D_ACTIONS.items():
            rating, beer_stats = action(beer)
            print('{}: {}'.format(site, rating))
            print(beer_stats)


def get_parser():

    parser = argparse.ArgumentParser(description=(''))
    parser.add_argument('bar', nargs='*')
    parser.add_argument('-f', nargs='*', default=[],
                        help='path/to/beerfile')
    parser.add_argument('--fancy', action='store_true',
                        help='~*~print fancy~*~ (default: false)')
    parser.add_argument('--sorted', action='store_true',
                        help='sort by average rating? (default: false)')
    parser.add_argument('--verbose', action='store_true',
                        help='verbose printing (e.g. for debugging)? (default: false)')
    # parser.add_argument('--filter-by', type=float, default=0,
    #                     help='minimum rating threshold (default: 0)')
    return parser


if __name__ == '__main__':
    # parse args
    args = get_parser().parse_args()

    assert args.bar or args.f, 'must supply bar or path/to/beerfile.. u drinking already ?'

    barquery = ' '.join(args.bar)
    beerfile = '\ '.join(args.f) # escape spaces

    alternate_main(barquery=barquery,
                   beerfile=beerfile,
                   fancy=args.fancy,
                   sorted_=args.sorted,
                   verbose=args.verbose)
