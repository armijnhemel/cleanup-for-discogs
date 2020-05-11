#!/usr/bin/env python3

## hackish script to process results of process-discogs-chunks.py
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017-2020 - Armijn Hemel

import os
import sys
import argparse
import collections
import defusedxml.minidom
import tlsh


def main():
    parser = argparse.ArgumentParser()

    # the following options are provided on the commandline
    parser.add_argument("-f", "--first", action="store", dest="first",
                        help="path to first file", metavar="FILE")
    parser.add_argument("-s", "--second", action="store", dest="second",
                        help="path to second file", metavar="FILE")
    parser.add_argument("-d", "--dir", action="store", dest="dir",
                        help="path to first dir", metavar="DIR")
    parser.add_argument("-e", "--seconddir", action="store", dest="seconddir",
                        help="path to second dir", metavar="DIR")
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

    if args.dir is None:
        parser.error("Path to first directory missing")

    if args.seconddir is None:
        parser.error("Path to second directory missing")

    release_to_sha1 = {}

    try:
        shafile1 = open(args.first, 'r')
    except:
        print("Could not open %s, exiting" % args.first, file=sys.stderr)
        sys.exit(1)

    for i in shafile1:
        (release_id, sha) = i.split('\t')
        release = int(release_id.split('.')[0])
        release_to_sha1[release] = sha.strip()

    shafile1.close()

    sha2_releases = set()

    try:
        shafile2 = open(args.second, 'r')
    except:
        print("Could not open %s, exiting" % args.second, file=sys.stderr)
        sys.exit(1)

    for i in shafile2:
        (release_id, sha) = i.split('\t')
        release = int(release_id.split('.')[0])
        if release in release_to_sha1:
            sha2_release = sha.strip()
            if release_to_sha1[release] != sha2_release:
                sha2_releases.add(release)

    shafile2.close()

    samecontent = 0
    differentcontent = 0
    release_to_tlsh_distance = {}
    tlshcounter = collections.Counter()

    for i in sorted(sha2_releases):
        firstfile = os.path.join(args.dir, "%d.xml" % i)
        if not os.path.exists(firstfile):
            continue
        secondfile = os.path.join(args.seconddir, "%d.xml" % i)
        if not os.path.exists(secondfile):
            continue
        firstdata = open(firstfile, 'rb').read()
        firsttlsh = tlsh.Tlsh()
        firsttlsh.update(firstdata)
        firsttlsh.final()
        seconddata = open(secondfile, 'rb').read()
        secondtlsh = tlsh.Tlsh()
        secondtlsh.update(seconddata)
        secondtlsh.final()
        distance = secondtlsh.diff(firsttlsh)
        release_to_tlsh_distance[i] = distance
        tlshcounter.update([distance])

    pos = 1
    print("Processed %d releases" % len(sha2_releases))
    for i in tlshcounter.most_common():
        print("%d:" % pos, "distance: %d, # %d" % i)
        pos += 1

if __name__ == "__main__":
    main()
