#! /usr/bin/python3

## Hackish example script to compare some results output by process-discogs-chunks.py
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017-2019 - Armijn Hemel

import os
import sys
import collections
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--shafile", action="store", dest="shafile",
                        help="path to file with SHA256/releases", metavar="FILE")
    parser.add_argument("-c", "--countryfile", action="store", dest="countryfile",
                        help="path to file with country names/releases", metavar="FILE")

    # the following options are provided on the commandline
    args = parser.parse_args()

    if args.shafile is None:
        parser.error("path to shafile missing")

    if args.countryfile is None:
        parser.error("path to countryfile missing")

    release_to_country = {}

    countriesfile = open(args.countryfile, 'r')

    for i in countriesfile:
        try:
            (release_id, country) = i.split('\t')
            release = release_id.split('.')[0]
            release_to_country[release] = i[1].strip()
        except:
            continue

    countriesfile.close()

    releases_set = set()

    releases_file = open(args.shafile, 'r')
    for i in releases_file:
        try:
            release_id = i.split('.', 1)[0]
            releases_set.add(release_id)
        except:
            continue

    releases_file.close()

    print(len(releases_set) - len(release_to_country))

    print(releases_set.difference(set(release_to_country.keys())))

if __name__ == "__main__":
    main()
