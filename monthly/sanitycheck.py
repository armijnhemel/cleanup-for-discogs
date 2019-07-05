#! /usr/bin/python3

## Hackish example script to compare some results output by process-discogs-chunks.py
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017-2019 - Armijn Hemel

import os, sys, collections

month = '201709'
countryfilename = '/gpl/tmp/out/country-%s' % month
shafilename = '/gpl/tmp/out/sha256-%s' % month

release_to_country = {}

countriesfile = open(countryfilename, 'r')

for i in countriesfile:
    (release_id, country) = i.split('\t')
    release = release_id.split('.')[0]
    release_to_country[release] = i[1].strip()

countriesfile.close()

releases_set = set()

releases_file = open(shafilename, 'r')
for i in releases_file:
    release_id = i.split('.',1)[0]
    releases_set.add(release_id)

releases_file.close()

print(len(releases_set) - len(release_to_country))

print(releases_set.difference(set(release_to_country.keys())))
