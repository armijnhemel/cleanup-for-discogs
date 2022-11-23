#!/usr/bin/env python3

# Quick and dirty script to see where differences in month are and where
# new errors were introduced in old releases. Only catches releases for
# which no previous errors were recorded.
#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright 2018-2022 - Armijn Hemel

import click

@click.command(short_help='process Discogs files and print releases that were different')
@click.option('--old', '-o', 'old_month', required=True, help='file with data from the old month', type=click.File('r'))
@click.option('--new', '-n', 'new_month', required=True, help='file with data from the new month', type=click.File('r'))
def main(old_month, new_month):
    # store the old releases, as a list, so order is kept
    oldreleases = []

    for i in old_month:
        try:
            oldrelease = int(i.strip().split('https://www.discogs.com/release/')[-1])
        except:
            continue

        if 'Tracklisting' in i:
            continue
        if 'Role' in i:
            continue
        if 'Artist' in i:
            continue
        oldreleases.append(oldrelease)

    # store the latest wrong release in the old release set. This is used
    # as a cut off value. It (falsely) assumes that this is the last release
    # but it could very well be that this is not the case (and this is because
    # Discogs does not include when a release was added in the XML data dump.
    latestoldrelease = oldreleases[-1]

    oldreleasesset = set(oldreleases)

    newreleases = []

    for i in new_month:
        try:
            newrelease = int(i.strip().split('https://www.discogs.com/release/')[-1])
        except:
            continue

        if newrelease > latestoldrelease:
            break
        if 'Tracklisting' in i:
            continue
        if 'Role' in i:
            continue
        if 'Artist' in i:
            continue
        if newrelease not in oldreleasesset:
            pass
            #print(i.strip())
        newreleases.append(newrelease)

    # Now check for each of the new releases if they are present
    # in the set of old releases. If not, it is a newly introduced
    # error and should be reported. Outputs data that can be fed
    # into makecharts.py
    for i in newreleases:
        if i not in oldreleasesset:
            print(' -- https://www.discogs.com/release/%d' % i)

if __name__ == "__main__":
    main()
