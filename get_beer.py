import itertools
import re
import requests

from bs4 import BeautifulSoup, element


def safe_encode(*args, pattern=' ', space_char='+'):
    """default: replace spaces with '+'
    """
    # SPACE_CHAR = '+'
    # return SPACE_CHAR.join(args).replace(' ', SPACE_CHAR)
    return re.sub(re.compile(pattern),
                  space_char,
                  space_char.join(args),
                  re.DOTALL)


def get_bar(barname):
    """

    """
    # BASE_URL = 'https://www.beermenus.com/search'
    BASE_URL = 'https://www.beermenus.com/{}'
    PARAMS = {'q': safe_encode(barname)}

    soup = BeautifulSoup(requests.get(BASE_URL.format('search'),
                                      PARAMS).content, 'lxml')

    top_hit = [match for match in soup('h3', class_='mb-0 text-normal')
               if match('a', href=re.compile('^/places/'))][0]

    hitname = top_hit.a.text
    hiturl = BASE_URL.format(top_hit.a['href'])
    # hiturl = re.sub('/search', top_hit.a['href'], BASE_URL)

    return hitname, hiturl


def get_beers(bar_url):
    """
    """
    soup = BeautifulSoup(requests.get(bar_url).content, 'lxml')

    beers = soup('a', href=re.compile('^/beers/'))

    beer_names = [beer.text for beer in beers]

    # get_beer_info = lambda tag: tag.next.next.next.next.text.replace(
    #     '\n','').split('·')

    # beer_types, beer_abvs, beer_places = (
    #     list(_) for _ in itertools.zip_longest(
    #         *(tuple(info.strip() for info in get_beer_info(beer))
    #           for beer in beers), fillvalue=''))

    return beer_names


# TODO wrapper to grab key from SECRETS
def get_reviews_ratebeer(query):
    """ Get beer stats

    :query: query beername str
    """
    BASE_URL = 'https://www.ratebeer.com/beer/{}/{}/'

    # def safe_encode_dashed(*args):
    #     SPACE_CHAR = '-'
    #     return re.sub(re.compile('[^\w\n]+'),
    #                   SPACE_CHAR,
    #                   SPACE_CHAR.join(args),
    #                   re.DOTALL)

    def query2name_id(query):
        """
        :query: beername query str
        :returns: (name, id)
        """
        # BASE_URL = 'https://api.ratebeer.com/v1/api/graphql/'
        BASE_URL = 'https://beta.ratebeer.com/v1/api/graphql/'

        data = {
            "query": "query beerSearch($query: String, $order: SearchOrder, $first: Int, $after: ID) { searchResultsArr: beerSearch(query: $query, order: $order, first: $first, after: $after) { totalCount last items { beer { id name overallScore ratingCount __typename } review { id score __typename } __typename   }   __typename } }",
            "variables": {"query": query, "order": "MATCH", " first": 20},
            "operationName":"beerSearch"
        }
        d_hits = (
            requests
            .post(BASE_URL,
                data=json.dumps(data),
                headers={"content-type": "application/json"})
            .json()['data']['searchResultsArr']
        )

        if d_hits['totalCount'] == 0: # no match found
            return # TODO

        top_hit = d_hits['items'][0]['beer']

        beername = top_hit['name']
        beer_id = top_hit['id']

        return BASE_URL

    # get stats
    beername, beer_id = query2name_id(query)
    soup = BeautifulSoup(requests.get(BASE_URL.format(
        safe_encode(beername, pattern='[^\w\n]+', space_char='-'),
        beer_id)).content, 'lxml')

    # mean rating = "?/5.0"
    rating = soup.find('a', attrs={'name': 'real average'}).strong.text

    # abv = "?%"
    abv = soup.find('abbr', title='Alcohol By Volume').next.next.next.strong.text

    # style
    style, = (tag.text for tag in soup('a', href=re.compile("^/beerstyles/"))
              if tag.previous == 'Style: ')

    # where


# TODO get_beerpage, get_beerinfo


def get_reviews_untappd(beerquery):
    """ Get beer stats

    :query: query beername str
    """
    BASE_URL = 'https://untappd.com/{}'

    def query2name_id(query):
        """
        :query: beername query str
        :returns: (name, id)
        """
        PARAMS = {'q': safe_encode(query)}

        soup = BeautifulSoup(requests.get(BASE_URL.format('search'),
                                          PARAMS).content, 'lxml')
