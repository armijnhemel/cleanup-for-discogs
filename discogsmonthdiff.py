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
        if 'Tracklisting' in i:
               continue
        if 'Role' in i:
               continue
        if 'Artist' in i:
               continue
        oldreleases.append(int((i.strip().split('https://www.discogs.com/release/')[-1])))

latestoldrelease = oldreleases[-1]

oldreleasesset = set(oldreleases)

newreleases = set()

for i in newmonth:
        newrelease = int(i.strip().split('https://www.discogs.com/release/')[-1])
        if newrelease > latestoldrelease:
                break
        if 'Tracklisting' in i:
               continue
        if 'Role' in i:
               continue
        if 'Artist' in i:
               continue
        if not newrelease in oldreleasesset:
                pass
                #print(i.strip())
        newreleases.add(newrelease)

#print(len(newreleases))

for i in oldreleases:
        if i not in newreleases:
                print(' -- https://www.discogs.com/release/%d' % i)

oldmonth.close()
newmonth.close()
