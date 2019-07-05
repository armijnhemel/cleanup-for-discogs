#! /usr/bin/python3

## Hackish example script to compare some results output by process-discogs-chunks.py
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017-2019 - Armijn Hemel

import os, sys

notaccepted1 = '/gpl/tmp/out/notaccepted-201708'
notaccepted2 = '/gpl/tmp/out/notaccepted-201709'

newdir = '/gpl/tmp/discogs/201709'

release_to_status1 = {}

notacceptedfile1 = open(notaccepted1, 'r')

for i in notacceptedfile1:
    (release_id, status) = i.split('\t')
    release = release_id.split('.')[0]
    release_to_status1[release] = i[1].strip()

notacceptedfile1.close()

release_to_status2 = {}

notacceptedfile2 = open(notaccepted2, 'r')

for i in notacceptedfile2:
    (release_id, status) = i.split('\t')
    release = release_id.split('.')[0]
    release_to_status2[release] = i[1].strip()

notacceptedfile2.close()

notkeys1 = set(release_to_status1.keys())
notkeys2 = set(release_to_status2.keys())

print("%d releases in not1 that are not in not2" % len(notkeys1.difference(notkeys2)))
print("%d releases in not2 that are not in not1" % len(notkeys2.difference(notkeys1)))

for i in notkeys1.difference(notkeys2):
    print(os.path.join(newdir, "%s.xml" % i), os.path.exists(os.path.join(newdir, "%s.xml" % i)))
