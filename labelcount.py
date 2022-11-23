#!/usr/bin/env python3

# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright Armijn Hemel


import collections
import sys
import os
import re

labelfilename = "label.txt"

labelregex = []
rx0 = re.compile('(?:lc)[\s/\-]*(\d{4,6})')

labelregex.append(rx0)

labelcounter = collections.Counter()

total = 0
valid = 0
ignored = 0

for i in open(labelfilename, 'r'):
    if not i.startswith('LABEL CODE'):
       continue
    total += 1
    labelcomponent = i.strip()[10:].strip().lower()
    labelcodefound = False
    for rx in labelregex:
        res = rx.match(labelcomponent)
        if res is not None:
            labelcode = res.groups()[0]
            if len(labelcode) == 4:
                labelcode = "00" + labelcode
            elif len(labelcode) == 5:
                labelcode = "0" + labelcode
            labelcounter.update([labelcode])
            labelcodefound = True
            break
    if labelcodefound:
        valid += 1
    else:
        ignored += 1

print("TOTAL: %d" % total)
print("VALID: %d" % valid)
print("IGNORED: %d" % ignored)
print("Labels: %d" % len(labelcounter))

counter = 1
for i in labelcounter.most_common():
    print(counter, "LC %s: %d" % i)
    counter += 1
