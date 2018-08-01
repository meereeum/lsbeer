```
$ lsbeer --sorted covenhoven

 what's on @ COVENHOVEN ?? 

100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 16/16 [00:20<00:00,  1.27s/it]

[ 4.22 |      | 4.37 ]  Industrial Arts Wrench IPA                             (ipa - new england, 6.8%)
[ 4.33 |      | 4.21 ]  Omnipollo Fatamorgana Double IPA Quadruple Dry Hopped  (ipa - imperial / double, 8%)
[ 4.12 |      | 4.25 ]  Alewife One Love                                       (pilsner - other, 5.5%)
[ 4.22 |      | 3.94 ]  Monday Night Brewing Ante Meridiem                     (brown ale - imperial / double, 13.5%)
[ 4.11 | 3.41 | 4.31 ]  Edmund's Oast Viridi Rex                               (ipa - imperial / double, 9.5%)
[ 4.02 | 3.45 | 4.19 ]  Omnipollo Alazar                                       (stout - imperial / double, 11%)
[ 3.98 | 3.45 | 3.95 ]  Edmunds Oast Bound by Time                             (ipa - american, 7%)
[ 3.86 |      | 3.7  ]  Finback Zero Point Coconut Gose                        (sour - gose, 6%)
[ 3.86 | 3.40 | 3.99 ]  Carton Eden                                            (saison / farmhouse ale, 6.2%)
[ 3.72 | 3.30 | 3.97 ]  Pipeworks Baklabot                                     (stout - other, 9%)
[ 3.59 |      |      ]  Shacksbury Arlo Cider                                  (cider - other, 6.9%)
[ 3.71 | 3.04 | 3.8  ]  Threes The World Is Flat                               (pale ale - english, 5.4%)
[ 3.7  | 3.29 | 3.52 ]  Revolution Freedom Of Speach                           (sour - ale, 4.5%)
[ 3.63 | 3.14 |      ]  Fifth hammer Lord Pennywhistle The Bemused             (pale ale - american, 5.8%)
[ 3.61 | 2.70 | 3.69 ]  Swiftwater Hefeweizen                                  (hefeweizen, 4.7%)
[ 3.55 | 2.87 |      ]  Brooklyn Cider House Raw Cider                         (cider - other, 6.9%)

[   untappd    |   ratebeer   | beeradvocate ]  ==  key
```

## more info

```
usage: get_beer.py [-h] [-f [F [F ...]]] [--sorted]
                   [--sort-by {untappd,ratebeer,beeradvocate}]
                   [--filter-by [FILTER_BY [FILTER_BY ...]]] [-a]
                   [--just-cans] [--fancy] [-t NTHREADS] [--interactive]
                   [--verbose]
                   [bar [bar ...]]

positional arguments:
  bar

optional arguments:
  -h, --help            show this help message and exit
  -f [F [F ...]]        path/to/beerfile
  --sorted              sort by average rating? (default: false)
  --sort-by {untappd,ratebeer,beeradvocate}
                        ratings website to sort by? (default: none)
  --filter-by [FILTER_BY [FILTER_BY ...]]
                        style/s to filter by? (default: all styles)
  -a, --all             taps AND cans & bottles ? (default: taps only)
  --just-cans           cans & bottles only ? (default: taps only)
  --fancy               ~*~print fancy~*~ (default: false)
  -t NTHREADS, --nthreads NTHREADS
                        number of threads (default: 4)
  --interactive         start IPython interactive session (e.g. to get more
                        beer info)? (default: false)
  --verbose             verbose printing (e.g. for debugging)? (default:
                        false)
```
