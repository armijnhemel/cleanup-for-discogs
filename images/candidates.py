#!/usr/bin/env python3

# Quick and dirty script to find candidates of releases that
# need to be looked at. Needs a directory of XML files extracted
# from the Discogs XML dump, using xml_split.
#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright 2019 - Armijn Hemel

# Usage:
#
# $ python3 candidates.py -d /tmp/spain/ -f /tmp/smells
#
# assuming that the directory /tmp/spain contains XML files extracted
# from Discogs and /tmp/smells a file with known releases per line
# with known depósito legal values.

import sys
import os
import argparse

import xml.dom.minidom

def main(argv):
    parser = argparse.ArgumentParser()

    # the following options are provided on the commandline
    parser.add_argument("-d", "--directory", action="store", dest="xmldir",
                        help="path to directory with XML files", metavar="DIR")
    parser.add_argument("-f", "--file", action="store", dest="smells",
                        help="path to file with release numbers with known smells", metavar="FILE")
    args = parser.parse_args()

    # first some sanity checks for the gzip compressed releases file
    if args.xmldir is None:
        parser.error("Data directory file missing")

    if not os.path.exists(args.xmldir):
        parser.error("Data directory file does not exist")

    if not os.path.isdir(args.xmldir):
        parser.error("Data directory is not a directory")

    if args.smells is None:
        parser.error("smells file missing")

    if not os.path.exists(args.smells):
        parser.error("smells file file does not exist")

    if not os.path.isfile(args.smells):
        parser.error("smells file is not a file")

    smells = set()
    smellsfile = open(args.smells, 'r')
    for s in smellsfile:
        smells.add(int(s.strip()))
    smellsfile.close()

    candidates = set()

    releases = os.listdir(args.xmldir)
    for r in releases:
        # open each file, read and check:
        # 1. is there an images element? If not exit.
        releasenr = int(r.rsplit('.')[0])
        if releasenr in smells:
            continue
        xmlfile = open(os.path.join(args.xmldir, r), 'rb')
        xmldata = xmlfile.read()
        xmlfile.close()
        if b'<description>7"' not in xmldata:
            continue
        #if b'<format name="Vinyl"' not in xmldata:
            #continue
        if b'<images>' not in xmldata:
            continue
        if b'<identifier type="Dep' in xmldata:
            continue
        if b'sito Legal' in xmldata:
            continue
        if b'sito legal' in xmldata:
            continue
        xmldom = xml.dom.minidom.parseString(xmldata)

        # get the images element
        try:
            images = xmldom.getElementsByTagName('image')
        except:
            continue
        candidates.add((releasenr, len(images)))

    candidatessorted = sorted(candidates, key=lambda x: x[1], reverse=True)
    counter = 1
    for c in candidatessorted:
        print(counter, 'https://www.discogs.com/release/%d' % c[0], c[1])
        counter += 1

if __name__ == "__main__":
    main(sys.argv)
