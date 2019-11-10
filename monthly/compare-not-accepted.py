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
import argparse

def main():
    parser = argparse.ArgumentParser()

    # the following options are provided on the commandline
    parser.add_argument("-f", "--first", action="store", dest="first",
                        help="path to first file", metavar="FILE")
    parser.add_argument("-s", "--second", action="store", dest="second",
                        help="path to second file", metavar="FILE")
    parser.add_argument("-a", "--all", action="store", dest="all",
                        help="path to all hashes (example: sha256-201909", metavar="FILE")
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

    if args.all is None:
        parser.error("Path to file with all hashes missing")

    if not os.path.exists(args.all):
        parser.error("All hashes file %s does not exist" % args.all)

    all_releases = set()

    try:
        shafile1 = open(args.all, 'r')
    except:
        print("Could not open %s, exiting" % args.all, file=sys.stderr)
        sys.exit(1)

    for i in shafile1:
        (release_id, sha) = i.split('\t')
        release = release_id.split('.')[0]
        all_releases.add(release)

    release_to_status1 = {}

    notacceptedfile1 = open(args.first, 'r')

    for i in notacceptedfile1:
        (release_id, status) = i.split('\t')
        release = release_id.split('.')[0]
        release_to_status1[release] = i[1].strip()

    notacceptedfile1.close()

    release_to_status2 = {}

    notacceptedfile2 = open(args.second, 'r')

    for i in notacceptedfile2:
        (release_id, status) = i.split('\t')
        release = release_id.split('.')[0]
        release_to_status2[release] = i[1].strip()

    notacceptedfile2.close()

    notkeys1 = set(release_to_status1.keys())
    notkeys2 = set(release_to_status2.keys())

    print("%d releases in not1 that are not in not2" % len(notkeys1.difference(notkeys2)))
    print("%d releases in not2 that are not in not1" % len(notkeys2.difference(notkeys1)))

    for i in sorted(notkeys1.difference(notkeys2)):
        print(i, i in all_releases)

if __name__ == "__main__":
    main()
