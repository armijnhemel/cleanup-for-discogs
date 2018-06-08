#!/usr/bin/python

## Quick and dirty script to see where differences in month are and where
## new errors were introduced in old releases. Only catches releases for
## which no previous errors were recorded.
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0-only
##
## Copyright 2018 - Armijn Hemel

oldmonth = open('/home/armijn/discogs-data/may2018.txt', 'r')
newmonth = open('/home/armijn/discogs-data/june2018.txt', 'r')

oldreleases = []

for i in oldmonth:
        oldreleases.append(int((i.strip().split('https://www.discogs.com/release/')[-1])))

latestoldrelease = oldreleases[-1]

oldreleasesset = set(oldreleases)

newreleases = set()

for i in newmonth:
        newrelease = int(i.strip().split('https://www.discogs.com/release/')[-1])
        if newrelease > latestoldrelease:
                break
        if not newrelease in oldreleasesset:
                newreleases.add(newrelease)
                print(i.strip())

#print(len(newreleases))

oldmonth.close()
newmonth.close()
