import argparse
from collections import defaultdict

from tqdm import tqdm

from CLIppy import fail_gracefully, flatten, get_from_file, safe_encode, soup_me

from scrapers import get_bar, get_beers, get_reviews_ratebeer, get_reviews_untappd, get_reviews_beeradvocate, get_beerpages_en_masse



def populate_beer_dict(beerlst, verbose=False):
    """
    lst of beers -> beerdict of sitesdicts of statsdicts
    """

    D_ACTIONS = {
        'untappd': get_reviews_untappd,
        'ratebeer': get_reviews_ratebeer,
        'beeradvocate': get_reviews_beeradvocate
    }

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





        try:


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

    reviewtxt = '{sep}'.join(['{:^6}'] * len(d_stats)).format(
        *(stats.get('rating', '') for stats in d_stats.values()),
        sep=sep)

    print('[{}]{spacer}{:<{width}}{spacer}({}, {})'.format(reviewtxt,
                                                           beer,
                                                           d_stats['untappd']['style'].lower(),
                                                           d_stats['untappd']['abv'],
                                                           width=maxwidth,
                                                           spacer=spacer))


@fail_gracefully
def alternate_main(barquery=None, beerfile=None, fancy=False, sorted_=False,
                   sort_by=None, verbose=False):

    if barquery:
        barname, bar_url = get_bar(barquery)
        beerlst = get_beers(bar_url)
    else:
        barname = beerfile.split('_')[-1]
        beerlst = get_beers_from_file(beerfile)

    print('\n what\'s on @ {} ?? \n'.format(barname.upper()))

    d_beers = populate_beer_dict(beerlst, verbose=verbose)
    print() # space after progress bar


    def get_avg_rating(beer):
        ratings = [float(d_stats['rating']) for d_stats in d_beers[beer].values()
                   if d_stats] # skip empty / not found
        try:
            avg = sum(ratings) / len(ratings)
        except(ZeroDivisionError):
            avg = -1 # no reviews found - list last

    MAXWIDTH = max((len(beer) for beer in beerlst))
    SPACER = '  '
    SEP = '|'

        return avg
    kwargs = {'spacer': SPACER, 'sep': SEP}
    if print_simple:
        kwargs['maxwidth'] = MAXWIDTH

    beerlst = (sorted(beerlst, key=lambda x: get_avg_rating(x), reverse=True) # best -> worst
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

    if not fancy: # print key
        # sites = D_ACTIONS.keys()
        sites = d_stats.keys() # leftover from leaky for-loop scope
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
