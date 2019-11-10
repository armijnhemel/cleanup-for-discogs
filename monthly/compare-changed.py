#!/usr/bin/python3

## hackish script to process results of process-discogs-chunks.py
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017-2019 - Armijn Hemel

import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser()

    # the following options are provided on the commandline
    parser.add_argument("-f", "--first", action="store", dest="first",
                        help="path to first file", metavar="FILE")
    parser.add_argument("-s", "--second", action="store", dest="second",
                        help="path to second file", metavar="FILE")
    parser.add_argument("-p", "--printchanged", action="store_true", dest="printchanged",
                        help="print changed entries instead of statistics")
    args = parser.parse_args()

    # then some sanity checks for the data files
    if args.first is None:
        parser.error("Path to first file missing")

    if not os.path.exists(args.first):
        parser.error("First file %s does not exist" % args.first)

    if args.second is None:
        parser.error("Path to second file missing")

    if not os.path.exists(args.second):
        parser.error("Second file %s does not exist" % args.second)

    release_to_sha1 = {}

    try:
        shafile1 = open(args.first, 'r')
    except:
        print("Could not open %s, exiting" % args.first, file=sys.stderr)
        sys.exit(1)

    for i in shafile1:
        (release_id, sha) = i.split('\t')
        release = release_id.split('.')[0]
        release_to_sha1[release] = sha.strip()

    shafile1.close()

    release_to_sha2 = {}

    try:
        shafile2 = open(args.second, 'r')
    except:
        print("Could not open %s, exiting" % args.second, file=sys.stderr)
        sys.exit(1)

    for i in shafile2:
        (release_id, sha) = i.split('\t')
        release = release_id.split('.')[0]
        release_to_sha2[release] = sha.strip()

    shafile2.close()

    shakeys1 = set(release_to_sha1.keys())
    shakeys2 = set(release_to_sha2.keys())

    if not args.printchanged:
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
                if args.printchanged:
                    print(' -- https://www.discogs.com/release/%s' % i)

    if not args.printchanged:
        print("SAME: %d" % samecontent)
        print("DIFFERENT: %d" % differentcontent)

if __name__ == "__main__":
    main()
