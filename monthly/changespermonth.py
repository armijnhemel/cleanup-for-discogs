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
import multiprocessing
import collections
import defusedxml.minidom
import tlsh

def process_release(firstdir, seconddir, releasenr):
    firstfile = os.path.join(firstdir, "%d.xml" % releasenr)
    if not os.path.exists(firstfile):
        return
    secondfile = os.path.join(seconddir, "%d.xml" % releasenr)
    if not os.path.exists(secondfile):
        return
    firstdata = open(firstfile, 'rb').read()

    firstxmldom = defusedxml.minidom.parseString(firstdata)
    seconddata = open(secondfile, 'rb').read()
    secondxmldom = defusedxml.minidom.parseString(seconddata)

    firstrelease = firstxmldom.getElementsByTagName('release')[0]
    secondrelease = secondxmldom.getElementsByTagName('release')[0]
    firstchilds = firstrelease.childNodes
    secondchilds = secondrelease.childNodes

    # store all differences found
    differences = []

    # check if any nodes were added or removed
    firstchildnames = set()
    secondchildnames = set()
    for ch in firstchilds:
        if ch.nodeName == 'videos':
            continue
        firstchildnames.add(ch.nodeName)
    for ch in secondchilds:
        if ch.nodeName == 'videos':
            continue
        secondchildnames.add(ch.nodeName)
    for n in firstchildnames - secondchildnames:
        differences.append(('removed', n))
    for n in secondchildnames - firstchildnames:
        differences.append(('added', n))

    # store the total TLSH score
    total_tlsh = 0

    # see if any nodes were changed by pretty printing
    # to XML first and then comparing the XML *shudder*
    for ch in firstchilds:
        if ch.nodeName == 'videos':
            continue
        for s in secondchilds:
            if ch.nodeName != s.nodeName:
                continue
            chxml = ch.toxml()
            sxml = s.toxml()
            if chxml != sxml:
                differences.append(('changed', ch.nodeName))
                firsttlsh = tlsh.Tlsh()
                firsttlsh.update(chxml.encode())
                try:
                    firsttlsh.final()
                except:
                    break
                secondtlsh = tlsh.Tlsh()
                secondtlsh.update(sxml.encode())
                try:
                    secondtlsh.final()
                except:
                    break
                distance = secondtlsh.diff(firsttlsh)
                total_tlsh += distance
            break
    return (differences, total_tlsh, releasenr)

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

    samecontent = 0

    # keep track of releases that are different and exist in
    # the first data set: new releases are ignored.
    for i in shafile2:
        (release_id, sha) = i.split('\t')
        release = int(release_id.split('.')[0])
        if release in release_to_sha1:
            sha2_release = sha.strip()
            if release_to_sha1[release] != sha2_release:
                sha2_releases.add(release)
            else:
                samecontent += 1

    shafile2.close()

    no_differences = set()

    # store the TLSH distance in separate data structures
    release_to_tlsh_distance = {}
    tlshcounter = collections.Counter()
    differencecounter = collections.Counter()

    # for each file see if the nodes are equal. Because Python's
    # DOM implementation doesn't implement DOM Level 3 this
    # is a bit of a hack. If DOM Level 3 were supported this
    # could be done by isEqualNode.
    pool = multiprocessing.Pool()
    res = pool.starmap(process_release, map(lambda x: (args.dir, args.seconddir, x), sha2_releases))
    for r in res:
        if r is None:
            continue
        (differences, total_tlsh, releasenr) = r
        if differences != []:
            differencecounter.update(differences)
            tlshcounter.update([total_tlsh])
        else:
            no_differences.add(releasenr)

    pos = 1
    print("Processed %d releases" % len(sha2_releases))
    for i in tlshcounter.most_common():
        print("%d:" % pos, "TLSH distance: %d, # %d" % i)
        pos += 1

    pos = 1
    for i in differencecounter.most_common():
        print("%d:" % pos, "change: %s, element %s" % i[0], "#: %d"% i[1])
        pos += 1

    print()
    print("No differences: %d" % len(no_differences))

if __name__ == "__main__":
    main()
