import argparse
from collections import defaultdict
import sys

import more_itertools
from tqdm import tqdm

from CLIppy import fail_gracefully, flatten, get_from_file, safe_encode, soup_me

from scrapers import get_bar, get_beers, get_reviews_ratebeer, get_reviews_untappd, get_reviews_beeradvocate, get_beerpages_en_masse

D_ACTIONS = {
    'untappd': get_reviews_untappd,
    'ratebeer': get_reviews_ratebeer,
    'beeradvocate': get_reviews_beeradvocate
}


def populate_beer_dict(beerlst, verbose=False):
    """
    lst of beers -> beerdict of sitesdicts of statsdicts
    """

    # D_ACTIONS = {
    #     'untappd': get_reviews_untappd,
    #     'ratebeer': get_reviews_ratebeer,
    #     'beeradvocate': get_reviews_beeradvocate
    # }

    def get_d_stats(beer):

        if verbose:
            print('looking up {} drinkability...'.format(beer.upper()))

        # dictionary of stats dictionaries
        d_stats = {
            site: action(beer, beerpage=get_beerpages_en_masse(beer).get(
                site, None)) # fallback is beerpage-specific search
            for site, action in D_ACTIONS.items()
        }

        if verbose:
            print('& done.')

        return d_stats

    # dict of sitedicts of statsdicts
    d_beers = {beer: get_d_stats(beer) for beer in tqdm(beerlst)} # <- progress bar

    return d_beers


def get_beers_from_file(f):
    """
    path/to/file -> list of beernames
    """
    return get_from_file(f=f)


def sort_beerlst(beerlst, d_beers, sorted_=False, sort_by=None):
    assert sorted_ or sort_by, 'Specify sorting by average or by site..'

    def get_avg_rating(beer):
        ratings = [float(d_stats['rating']) for d_stats in d_beers[beer].values()
                   if d_stats and d_stats.__contains__('rating')] # skip empty / not found
                   # if d_stats and d_stats['rating']] # skip empty / not found
        try:
            avg = sum(ratings) / len(ratings)
        except(ZeroDivisionError):
            avg = -1 # no reviews found - list last

        return avg

    def get_rating_by_site(beer, site):
        try:
            rating = d_beers[beer][site]['rating']
            # assert rating
        # except(KeyError, AssertionError):
        except(KeyError):
            rating = -1 # no review found - list last

        return rating

    KEY = (get_avg_rating if sorted_ else                              # avg review
           lambda x: (get_rating_by_site(x, sort_by), get_avg_rating)) # by site, then avg

    return sorted(beerlst, key=KEY, reverse=True) # best -> worst


def print_fancy(beer, d_stats, sep='|', spacer='  '):
    PATTERN = '~*~'
    # SPACER = '  '
    # SEP = '|'

    # d_reviews = {k: v['rating'] for k,v in d_stats.items()
    #              if v} # skip empty / not found

    style = get_info_ranked('style')
    abv = get_info_ranked('abv')

    # header
    print('\n{pattern} {} {pattern} ({}, {})\n'.format(beer,
                                                       style, #d_stats['untappd']['style'],
                                                       abv, #d_stats['untappd']['abv'],
                                                       pattern=PATTERN))

    # reviews
    sitetxt = ''.join(
        ('{spacer}',
         # '{spacer}{sep}{spacer}'.join(['({})'] * len(d_stats)),
         '{spacer}{sep}{spacer}'.join(['({})'] * len(D_ACTIONS)),
         # '{spacer}')).format(*d_stats.keys(), spacer=spacer, sep=sep)
         '{spacer}')).format(*D_ACTIONS.keys(), spacer=spacer, sep=sep)
    # sitetxt = ''.join(
    #     ('{spacer}',
    #      '{spacer}{sep}{spacer}'.join(['({})'] * len(d_reviews)),
    #      '{spacer}')).format(*d_reviews.keys(), spacer=SPACER, sep=SEP)
    # sitetxt = '{spacer}({}){spacer}{sep}{spacer}({}){spacer}{sep}{spacer}({}){spacer}'.format(*d_reviews.keys(), spacer=SPACER, sep=SEP)

    widths = (len(_) for _ in sitetxt.split(sep))

    # reviewtxt = '{sep}'.join(['{:^{}}'] * len(d_stats)).format(
    #     *flatten(zip((stats.get('rating', '') for stats in d_stats.values()),
    #                  widths)), sep=sep)
    reviewtxt = '{sep}'.join(['{:^{}}'] * len(D_ACTIONS)).format(
        *flatten(zip((stats.get('rating', '') for site, stats in d_stats.items()
                      if site in D_ACTIONS.keys()), # ratings sites only
                     widths)), sep=sep)
    # reviewtxt = '{sep}'.join(['{:^{}}'] * len(d_reviews)).format(
    #     *flatten(zip(d_reviews.values(), widths)), sep=SEP)
    # reviewtxt = '{:^{}}{sep}{:^{}}{sep}{:^{}}'.format(
    #     *flatten(zip(d_reviews.values(), widths)), sep=SEP)

    print('\n'.join((reviewtxt, sitetxt)))
    print()


def get_info_ranked(d_stats, k_info, l_ranked_ks=['untappd', 'beermenus',
                                                  'ratebeer', 'beeradvocate']):
    """
    dict of beer stats, key for info, list of ranked keys -> info under highest ranked key available
       i.e. d_stats[highest_ranked_k_in_l][k_info]
    """
    if not l_ranked_ks: # base case: info not found in any of ranked keys
        return ''

    top_k, *rest = l_ranked_ks
    try:
        return d_stats[top_k][k_info]
    except(KeyError):
        return get_info_ranked(d_stats, k_info, rest)


def print_simple(beer, d_stats, maxwidth, sep='|', spacer='  '):
    # SPACER = '  '
    # SEP = '|'

    # reviewtxt = '{sep}'.join(['{:^6}'] * len(d_stats)).format(
    #     *(stats.get('rating', '') for stats in d_stats.values()),
    #     sep=sep)
    # reviewtxt = '{sep}'.join(['{:^6}'] * len(d_stats)).format(
    reviewtxt = '{sep}'.join(['{:^6}'] * len(D_ACTIONS)).format(
        *(stats.get('rating', '') for site, stats in d_stats.items()
          if site in D_ACTIONS.keys()), # rating sites only
        sep=sep)

    # get_info_ranked = lambda l_ks: d_stats.get(
    #     l_ks[0], get_info_ranked(l_ks[1:]))

    # def get_info_ranked(k_info, l_ranked_ks):
    #     """
    #     list of ranked keys, key for info -> info under highest ranked key available
    #     """
    #     if not l_ranked_ks: # base case: info not found in any of ranked keys
    #         info = ''

    #     top_k, *rest = l_ranked_ks
    #     try:
    #         # info = d_stats[l_ranked_ks[0]][k_info]
    #         info = d_stats[top_k][k_info]
    #     except(KeyError):
    #         # info = get_info_ranked(k_info, l_ranked_ks[1:])
    #         info = get_info_ranked(k_info, rest)
    #     return info

    # style = d_stats.get('untappd', # 1st choice + backup
    #                     d_stats.get('beermenus'))['style'].lower()

    # abv = d_stats.get('untappd', # 1st choice + backup
    #                   d_stats.get('beermenus'))['abv']
    # SITES_RANKED = ['untappd', 'beermenus', 'ratebeer', 'beeradvocate']

    # style = get_info_ranked('style', SITES_RANKED).lower()
    # abv = get_info_ranked('abv', SITES_RANKED)
    style = get_info_ranked(d_stats, 'style').lower()
    abv = get_info_ranked(d_stats, 'abv')

    print('[{}]{spacer}{:<{width}}{spacer}({}, {})'.format(reviewtxt,
                                                           beer,
                                                           style,# d_stats['untappd']['style'].lower(),
                                                           abv,# d_stats['untappd']['abv'],
                                                           width=maxwidth,
                                                           spacer=spacer))


@fail_gracefully
def outer_main(barquery=None, beerfile=None, fancy=False, sorted_=False,
               sort_by=None, filter_by=[], get_taps=True, get_cans=False,
               verbose=False):

    if barquery:
        barname, bar_url = get_bar(barquery)
        # beerlst, n_on_tap = get_beers(bar_url)
        # d_beers_beermenus, n_on_tap = get_beers(bar_url)
        # beerlst = list(d_beers.keys())
        d_beermenus = get_beers(bar_url)
        # beerlst = list(d_beers.keys())

        # isnt_on_tap = lambda beer: (
        #     'draft' not in set(d['type'] for d in d_stats[beer]['serving']))

        # get_servingtypes = lambda beer: set(
        #     d['type'] for d in d_stats[beer]['serving'])

        def is_served_as(beer, *args):
            servingtypes = set(d['type'] for d in d_beermenus[beer]['serving'])
            return any(arg in servingtypes for arg in args)

        is_on_tap = lambda beer: is_served_as(beer, 'draft', 'cask')
        is_bottled = lambda beer: is_served_as(beer, 'bottle', 'can')

        # on_draft, not_on_draft = more_itertools.partition(isnt_on_tap, d_stats.keys())
        # beerlst, rest = more_itertools.partition(isnt_on_tap, d_stats.keys())

        beerlst = [beer for beer in d_beermenus.keys() if is_on_tap(beer)]
        beerlst_rest = [beer for beer in d_beermenus.keys() if is_bottled(beer)]

    else:
        barname = beerfile.split('_')[-1]
        beerlst = get_beers_from_file(beerfile)
        # on_draft = get_beers_from_file(beerfile)
        d_beermenus = {}#; n_on_tap = len(beerlst)

    print('\n what\'s on @ {} ?? \n'.format(barname.upper()))

    kwargs = {
        'd_beermenus': d_beermenus,
        'fancy': fancy,
        'sorted_': sorted_,
        'sort_by': sort_by,
        'filter_by': filter_by,
        'verbose': verbose
    }

    if beerfile or (barquery and get_taps):
        # beerlst_taps = beerlst[:n_on_tap]
        beerlst_taps = beerlst
        alternate_main(beerlst_taps, with_key=(not get_cans), **kwargs)
        # alternate_main(beerlst_taps, d_beers_extra=d_beers_beermenus,
        #                fancy=fancy, sorted_=sorted_, sort_by=sort_by,
        #                filter_by=filter_by, verbose=verbose,
        #                with_key=(not get_cans))

    if barquery and get_cans:
        print('CANS & BOTTLES...')
        # beerlst_cans = beerlst[n_on_tap:]
        beerlst_cans = beerlst_rest
        alternate_main(beerlst_cans, with_key=get_cans, **kwargs)
        # alternate_main(beerlst_cans, d_beers_extra=d_beers_beermenus, fancy=fancy, sorted_=sorted_,
        #                sort_by=sort_by, filter_by=filter_by, verbose=verbose,
        #                with_key=get_taps)


def word_intersection(*args):
    """
    strs / lists -> word intersection
    """
    args = ((arg.lower().split() if isinstance(arg, str) # str -> list
             else (a.lower() for a in arg)) # lst -> lowerlst
            for arg in args)
    return set.intersection(*(set(arg) for arg in args))


def alternate_main(beerlst, fancy=False, sorted_=False, sort_by=None,
                   filter_by=[], d_beermenus={}, verbose=False, with_key=False):
    d_beers = populate_beer_dict(beerlst, verbose=verbose)
    print() # space after progress bar

    # augment with beermenus data
    for beer in beerlst:
        d_beers[beer]['beermenus'] = d_beermenus.get(beer, {})

    # filter
    get_style = lambda x: d_beers[x]['untappd']['style']
    beerlst = ([beer for beer in beerlst if word_intersection(get_style(beer),
                                                              filter_by)]
               if filter_by else beerlst)
    if not beerlst:
        print('overly filtered beers\n')
        sys.exit(0)

    # sort
    beerlst = (sort_beerlst(beerlst, d_beers, sorted_=sorted_, sort_by=sort_by)
               if (sorted_ or sort_by) else beerlst)

    # print
    MAXWIDTH = max((len(beer) for beer in beerlst))
    SPACER = '  '
    SEP = '|'

    kwargs = {'spacer': SPACER, 'sep': SEP}
    if not fancy:
        kwargs['maxwidth'] = MAXWIDTH

    pprint = print_fancy if fancy else print_simple

    # pprint = (print_fancy if fancy else
    #           lambda *args, **kwargs: print_simple(
    #               *args, **kwargs, maxwidth=MAXWIDTH))

    for beer in beerlst:

        d_stats = d_beers[beer]

        if not d_stats: # no reviews found
            print('\nskipping {}...\n'.format(beer))
            continue

        # take consensus
        # d_stats_consensus = defaultdict(lambda: [])
        # d_stats_squashed = {defaultdict(lambda: [])}

        pprint(beer, d_stats, **kwargs)

    if with_key and not fancy: # print key
        sites = D_ACTIONS.keys()
        # sites = d_stats.keys() # leftover from leaky for-loop scope
        maxsitewidth = max((len(site) for site in sites))
        sitetxt = '{sep}'.join(['{:^{width}}'] * len(sites)).format(*sites,
                                                                    sep=SEP,
                                                                    width=maxsitewidth + 2)
        print('\n[{}]{spacer}=={spacer}key\n'.format(sitetxt, spacer=SPACER))


def get_parser():

    parser = argparse.ArgumentParser(description=(''))
    parser.add_argument('bar', nargs='*')
    parser.add_argument('-f', nargs='*', default=[],
                        help='path/to/beerfile')
    parser.add_argument('--sorted', action='store_true',
                        help='sort by average rating? (default: false)')
    parser.add_argument('--sort-by', default=None,
                        choices=D_ACTIONS.keys(),
                        # choices=['untappd', 'ratebeer', 'beeradvocate'],
                        help='ratings website to sort by? (default: none)')
    parser.add_argument('--filter-by', nargs='*', default=[],
                        help='style/s to filter by? (default: all styles)')
    parser.add_argument('-a', '--all', action='store_true',
                        help='taps AND cans & bottles ? (default: taps only)')
    parser.add_argument('--just-cans', action='store_true',
                        help='cans & bottles only ? (default: taps only)')
    parser.add_argument('--fancy', action='store_true',
                        help='~*~print fancy~*~ (default: false)')
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

    # alternate_main(barquery=barquery,
    outer_main(barquery=barquery,
               beerfile=beerfile,
               fancy=args.fancy,
               sorted_=args.sorted,
               sort_by=args.sort_by,
               filter_by=args.filter_by,
               verbose=args.verbose,
               get_taps=(not args.just_cans),
               get_cans=(args.all or args.just_cans))
