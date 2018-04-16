import argparse
from collections import defaultdict
import sys

import more_itertools
from tqdm import tqdm

from CLIppy import dedupe, fail_gracefully, flatten, get_from_file, safe_encode, soup_me

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

    # beerlst = (sorted(beerlst, key=KEY, reverse=True) # best -> worst
    #            if (sorted_ or sort_by) else beerlst)
    # beerlst = (sorted(beerlst, key=get_avg_rating, reverse=True) # best -> worst
    #            if sorted_ else beerlst)
    #
    # return beerlst

    return sorted(beerlst, key=KEY, reverse=True) # best -> worst


def print_fancy(beer, d_stats, sep='|', spacer='  '):
    PATTERN = '~*~'
    # SPACER = '  '
    # SEP = '|'

    # d_reviews = {k: v['rating'] for k,v in d_stats.items()
    #              if v} # skip empty / not found

    # header
    print('\n{pattern} {} {pattern} ({}, {})\n'.format(beer,
                                                       d_stats['untappd']['style'],
                                                       d_stats['untappd']['abv'],
                                                       pattern=PATTERN))

    # reviews
    sitetxt = ''.join(
        ('{spacer}',
         '{spacer}{sep}{spacer}'.join(['({})'] * len(d_stats)),
         '{spacer}')).format(*d_stats.keys(), spacer=spacer, sep=sep)
    # sitetxt = ''.join(
    #     ('{spacer}',
    #      '{spacer}{sep}{spacer}'.join(['({})'] * len(d_reviews)),
    #      '{spacer}')).format(*d_reviews.keys(), spacer=SPACER, sep=SEP)
    # sitetxt = '{spacer}({}){spacer}{sep}{spacer}({}){spacer}{sep}{spacer}({}){spacer}'.format(*d_reviews.keys(), spacer=SPACER, sep=SEP)

    widths = (len(_) for _ in sitetxt.split(sep))

    reviewtxt = '{sep}'.join(['{:^{}}'] * len(d_stats)).format(
        *flatten(zip((stats.get('rating', '') for stats in d_stats.values()),
                     widths)), sep=sep)
    # reviewtxt = '{sep}'.join(['{:^{}}'] * len(d_reviews)).format(
    #     *flatten(zip(d_reviews.values(), widths)), sep=SEP)
    # reviewtxt = '{:^{}}{sep}{:^{}}{sep}{:^{}}'.format(
    #     *flatten(zip(d_reviews.values(), widths)), sep=SEP)

    print('\n'.join((reviewtxt, sitetxt)))
    print()


def print_simple(beer, d_stats, maxwidth, sep='|', spacer='  '):
    # SPACER = '  '
    # SEP = '|'

    # reviewtxt = '{sep}'.join(['{:^6}'] * len(d_stats)).format(
    #     *(stats.get('rating', '') for stats in d_stats.values()),
    #     sep=sep)
    reviewtxt = '{sep}'.join(['{:^6}'] * len(d_stats)).format(
        *(stats.get('rating', '') for site, stats in d_stats.items()
          if site in D_ACTIONS.keys()), # rating stes only
        sep=sep)

    print('[{}]{spacer}{:<{width}}{spacer}({}, {})'.format(reviewtxt,
                                                           beer,
                                                           d_stats['untappd']['style'].lower(),
                                                           d_stats['untappd']['abv'],
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
        d_beers_beermenus = get_beers(bar_url)
        # beerlst = list(d_beers.keys())

        isnt_on_tap = lambda beer: (
            'draft' not in set(d['type'] for d in d_stats[beer]['serving']))
        # on_draft, not_on_draft = more_itertools.partition(isnt_on_tap, d_stats.keys())
        beerlst, rest = more_itertools.partition(isnt_on_tap, d_stats.keys())

    else:
        barname = beerfile.split('_')[-1]
        beerlst = get_beers_from_file(beerfile)
        # on_draft = get_beers_from_file(beerfile)
        d_beers_beermenus = {}#; n_on_tap = len(beerlst)

    print('\n what\'s on @ {} ?? \n'.format(barname.upper()))

    kwargs = {
        'd_beers_beermenus': d_beers_beermenus,
        'fancy': fancy,
        'sorted_': sorted_,
        'sort_by': sort_by,
        'filter_by': filter_by
        'verbose': verbose
    }

    if beerfile or (barquery and get_taps):
        # beerlst_taps = beerlst[:n_on_tap]
        beerlst_taps = beerlst #on_draft
        alternate_main(beerlst_taps, with_key=(not get_cans), **kwargs)
        # alternate_main(beerlst_taps, d_beers_extra=d_beers_beermenus,
        #                fancy=fancy, sorted_=sorted_, sort_by=sort_by,
        #                filter_by=filter_by, verbose=verbose,
        #                with_key=(not get_cans))

    if barquery and get_cans:
        print('CANS & BOTTLES...')
        # beerlst_cans = beerlst[n_on_tap:]
        beerlst_cans = rest #not_on_draft
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
                   filter_by=[], d_beers_beermenus={}, verbose=False, with_key=False):
    beerlst = dedupe(beerlst) # occasional conflict b/w taps vs growlers
    d_beers = populate_beer_dict(beerlst, verbose=verbose)
    d_beers.update(((beer, {'beermenus': d_beers_beermenus.get(beer,{})})
                   for beer in beerlst))
    print() # space after progress bar

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
