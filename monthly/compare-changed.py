#!/usr/bin/python3

## hackish script to process results of process-discogs-chunks.py
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017 - Armijn Hemel

import os, sys, collections

shafilename1 = '/home/armijn/tmp/sha256-201906'
shafilename2 = '/home/armijn/tmp/sha256-201907'

release_to_sha1 = {}

shafile1 = open(shafilename1, 'r')

for i in shafile1:
    (release_id, sha) = i.split('\t')
    release = release_id.split('.')[0]
    release_to_sha1[release] = sha.strip()

shafile1.close()

release_to_sha2 = {}

shafile2 = open(shafilename2, 'r')

for i in shafile2:
    (release_id, sha) = i.split('\t')
    release = release_id.split('.')[0]
    release_to_sha2[release] = sha.strip()

shafile2.close()

shakeys1 = set(release_to_sha1.keys())
shakeys2 = set(release_to_sha2.keys())

print("MONTH 1: %d" % len(shakeys1), "MONTH 2: %d" % len(shakeys2))

print("%d releases in sha1 that are not in sha2" % len(shakeys1.difference(shakeys2)))
print("%d releases in sha2 that are not in sha1" % len(shakeys2.difference(shakeys1)))

samecontent = 0
differentcontent = 0

for i in release_to_sha2:
    if i in release_to_sha1:
        if release_to_sha1[i] == release_to_sha2[i]:
            samecontent += 1
        else:
            differentcontent += 1

print("SAME: %d" % samecontent)
print("DIFFERENT: %d" % differentcontent)
