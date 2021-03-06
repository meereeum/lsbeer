import argparse
from collections import defaultdict
import re
import sys

from tqdm import tqdm

from CLIppy import fail_gracefully, flatten, get_from_file, safe_encode, soup_me

from scrapers import get_bar, get_beers, get_reviews_ratebeer, get_reviews_untappd, get_reviews_beeradvocate, get_beerpages_en_masse



D_ACTIONS = dict(
    untappd = get_reviews_untappd,
    ratebeer = get_reviews_ratebeer,
    beeradvocate = get_reviews_beeradvocate
)


def get_d_stats(beer, verbose=False):
    # fn must be outer to be pickleable, and therefore eligible for multiprocessing

    if verbose:
        print('looking up {} drinkability...'.format(beer.upper()))

    # dictionary of stats dictionaries
    d_stats = {
        site: action(beer, verbose=verbose,
                     # fallback is beerpage-specific search
                     beerpage=get_beerpages_en_masse(beer).get(site, None))
        for site, action in D_ACTIONS.items()
    }

    if verbose:
        print('& done.')

    return d_stats


def populate_beer_dict(beerlst, nthreads=4, verbose=False):
    """
    lst of beers -> beerdict of sitesdicts of statsdicts
    """

    if nthreads > 1:
        from multiprocessing import Pool

        # TODO verbose not passed
        # via https://stackoverflow.com/questions/41920124/multiprocessing-use-tqdm-to-display-a-progress-bar
        with Pool(nthreads) as p:
            d_beers = dict(zip(beerlst, list( # list needed to finalize itable for tqdm
                tqdm(p.imap(get_d_stats, beerlst), # <- progress bar
                     total=len(beerlst)))))

    else:
        d_beers = {beer: get_d_stats(beer, verbose=verbose)
                   for beer in tqdm(beerlst)} # <- progress bar

    return d_beers # dict of sitedicts of statsdicts


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
        try:
            avg = sum(ratings) / len(ratings)
        except(ZeroDivisionError):
            avg = -1 # no reviews found - list last

        return avg

    def get_rating_by_site(beer, site):
        try:
            rating = d_beers[beer][site]['rating']
        except(KeyError):
            rating = -1 # no review found - list last

        return rating

    KEY = (get_avg_rating if sorted_ else                              # avg review
           lambda x: (get_rating_by_site(x, sort_by), get_avg_rating)) # by site, then avg

    return sorted(beerlst, key=KEY, reverse=True) # best -> worst


def print_fancy(beer, d_stats, sep='|', spacer='  ', **kwargs):
    PATTERN = '~*~'
    # SPACER = '  '
    # SEP = '|'

    # d_reviews = {k: v['rating'] for k,v in d_stats.items()
    #              if v} # skip empty / not found

    style = get_info_ranked('style')
    abv   = get_info_ranked('abv')

    # header
    print('\n{pattern} {} {pattern} ({}, {})\n'.format(beer,
                                                       style,
                                                       abv,
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


def get_info_consensus(d_stats, k_info):
    """
    dict of beer stats, key for info -> consensus info under key across sites
    """
    # try: TODO currently, must be common to all
    #     word_intersection(*(d[k_info] for d in d_stats.values()
    #                         if d.__contains__('k_info')))
    # TODO
    pass


def print_simple(beer, d_stats, maxwidth, maxstylewidth, sep='|', spacer=' ',
                 terse=True, **kwargs):

    reviewtxt = '{sep}'.join(['{:^6}'] * len(D_ACTIONS)).format(
        *(stats.get('rating', '') for site, stats in d_stats.items()
          if site in D_ACTIONS.keys()), # rating sites only
        sep=sep)

    style = get_info_ranked(d_stats, 'style').lower()
    abv   = get_info_ranked(d_stats, 'abv')

    if terse:
        style = re.sub(' -.*$', '', style)

    print('[{}]{spacer}{:<{width}}{spacer}({} · {})'.format(reviewtxt,
    #print('[{}]{spacer}{:<{width}}{spacer}({:<{stylewidth}} · {:>3})'.format(reviewtxt,
                                                            beer,
                                                            style,
                                                            abv,
                                                            width=maxwidth,
                                                            #stylewidth=maxstylewidth,
                                                            spacer=spacer))


@fail_gracefully
def outer_main(barquery=None, beerfile=None, get_taps=True, get_cans=False,
               interactive=False, **kwargs):

    if barquery:
        barname, bar_url = get_bar(barquery)
        # beerlst, n_on_tap = get_beers(bar_url)
        # d_beers_beermenus, n_on_tap = get_beers(bar_url)
        d_beermenus = get_beers(bar_url)
        kwargs['d_beermenus'] = d_beermenus

        def is_served_as(beer, *args):
            servingtypes = {d['type'].lower() for d in d_beermenus[beer]['serving']}
            return any(arg in servingtypes for arg in args)

        is_on_tap = lambda beer: is_served_as(beer, 'draft', 'cask', 'crowler', 'growler')
        is_bottled = lambda beer: is_served_as(beer, 'bottle', 'can')

        has_no_servinginfo = lambda beer: not d_beermenus[beer]['serving']

        beerlst = [beer for beer in d_beermenus.keys() if (is_on_tap(beer) or
                                                           has_no_servinginfo(beer))]
        beerlst_rest = [beer for beer in d_beermenus.keys() if is_bottled(beer)]

        if barname.lower() == 'covenhoven': # TODO drafts listed as bottle - eventually fix for good
            beerlst = list(d_beermenus.keys())
            beerlst_rest = []

    else:
        barname = beerfile.split('_')[-1]
        beerlst = get_beers_from_file(beerfile)
        # on_draft = get_beers_from_file(beerfile)
        d_beermenus = {}#; n_on_tap = len(beerlst)

    print('\n what\'s on @ {} ?? \n'.format(barname.upper()))

    if beerfile or (barquery and get_taps):
        # beerlst_taps = beerlst[:n_on_tap]
        beerlst_taps = beerlst
        d_beers1 = alternate_main(beerlst_taps, with_key=(not get_cans), **kwargs)

    if barquery and get_cans:
        print('\nCANS & BOTTLES...\n')
        # beerlst_cans = beerlst[n_on_tap:]
        beerlst_cans = beerlst_rest
        d_beers2 = alternate_main(beerlst_cans, with_key=get_cans, **kwargs)

    if interactive:
        from itertools import chain
        for k, v in chain(d_beers1.items(), d_beers2.items()):
            d_beers = d_beermenus[k].update(**v)

        import IPython; IPython.embed()


def word_intersection(*args):
    """
    strs / lists -> word intersection
    """
    args = ((arg.lower().split() if isinstance(arg, str) # str -> list
             else (a.lower() for a in arg)) # lst -> lowerlst
            for arg in args)
    return set.intersection(*(set(arg) for arg in args))


def alternate_main(beerlst, d_beermenus={}, fancy=False, sorted_=False,
                   sort_by=None, filter_by=[], nthreads=1, verbose=False,
                   with_key=False):

    d_beers = populate_beer_dict(beerlst, nthreads=nthreads, verbose=verbose)
    print() # space after progress bar

    # augment with beermenus data
    for beer in beerlst:
        d_beers[beer]['beermenus'] = d_beermenus.get(beer, {})

    # filter
    #get_style = lambda x: d_beers[x]['untappd']['style']
    get_style = lambda x: [d.get('style', '') for d in
                           d_beers[x].values()]

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
    MAXSTYLEWIDTH = max((len(get_style(beer)) for beer in beerlst))
    SPACER = '  '
    SEP = '|'

    kwargs = dict(
        spacer = SPACER,
        sep = SEP,
        maxwidth = MAXWIDTH,
        maxstylewidth = MAXSTYLEWIDTH
    )
    pprint = print_fancy if fancy else print_simple

    for beer in beerlst:

        d_stats = d_beers[beer]

        # shld only happen with non-beermenus beer (i.e. from file)
        if not any(v for v in d_stats.values()): # no data found
            print('\nskipping {}...\n'.format(beer))
            continue

        # take consensus
        # d_stats_consensus = defaultdict(lambda: [])
        # d_stats_squashed = {defaultdict(lambda: [])}

        pprint(beer, d_stats, **kwargs)

    if with_key and not fancy: # print key
        sites = D_ACTIONS.keys()
        maxsitewidth = max((len(site) for site in sites))
        sitetxt = '{sep}'.join(['{:^{width}}'] * len(sites)).format(*sites,
                                                                    sep=SEP,
                                                                    width=maxsitewidth + 2)
        print('\n[{}]{spacer}=={spacer}key\n'.format(sitetxt, spacer=SPACER))

    return d_beers


def get_parser():

    parser = argparse.ArgumentParser(description=(''))
    parser.add_argument('bar', nargs='*')
    parser.add_argument('-f', nargs='*', default=[],
                        help='path/to/beerfile')
    parser.add_argument('--sorted', action='store_true',
                        help='sort by average rating? (default: false)')
    parser.add_argument('--sort-by', default=None,
                        choices=D_ACTIONS.keys(),
                        help='ratings website to sort by? (default: none)')
    parser.add_argument('--filter-by', nargs='*', default=[],
                        help='style/s to filter by? (default: all styles)')
    parser.add_argument('-a', '--all', action='store_true',
                        help='taps AND cans & bottles ? (default: taps only)')
    parser.add_argument('--just-cans', action='store_true',
                        help='cans & bottles only ? (default: taps only)')
    parser.add_argument('--fancy', action='store_true',
                        help='~*~print fancy~*~ (default: false)')
    parser.add_argument('-t', '--nthreads', type=int, default=4,
                        help='number of threads (default: 4)')
    parser.add_argument('--interactive', action='store_true',
                        help='start IPython interactive session (e.g. to get more beer info)? (default: false)')
    parser.add_argument('--verbose', action='store_true',
                        help='verbose printing (e.g. for debugging)? (default: false)')
    # parser.add_argument('--filter-by', type=float, default=0,
    #                     help='minimum rating threshold (default: 0)')
    return parser


if __name__ == '__main__':
    # parse args
    args = get_parser().parse_args()

    try:
        assert args.bar or args.f, 'must supply bar or path/to/beerfile.. u drinking already ?'
    except(AssertionError) as e:
        exit_txt, = e.args
        print(exit_txt)
        sys.exit(0)

    barquery = ' '.join(args.bar)
    beerfile = '\ '.join(args.f) # escape spaces

    # alternate_main(barquery=barquery,
    outer_main(barquery=barquery,
               beerfile=beerfile,
               fancy=args.fancy,
               sorted_=args.sorted,
               sort_by=args.sort_by,
               filter_by=args.filter_by,
               nthreads=args.nthreads,
               interactive=args.interactive,
               verbose=args.verbose,
               get_taps=(not args.just_cans),
               get_cans=(args.all or args.just_cans))
