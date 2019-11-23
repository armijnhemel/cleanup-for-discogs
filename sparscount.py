#/usr/bin/env python3

# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright Armijn Hemel


import collections
import sys
import os
import re

sparsfilename = "dl.txt"
seps = ['.', '·', '•', '∙']

sparsregex = []
rx0 = re.compile('([ad]\s*[ad]\s*[ad])$')
rx1 = re.compile('\[([ad]{3})\]$')
rx2 = re.compile('([ad]{3}),\s*([ad]{3})$')
rx3 = re.compile('([ad]{3})\s*/\s*([ad]{3})$')
rx4 = re.compile('([ad]{3})\s*&\s*([ad]{3})$')
rx5 = re.compile('([ad]{3})\s*\|\s*([ad]{3})$')
rx6 = re.compile('([ad]{3})\s*\+\s*([ad]{3})$')
rx7 = re.compile('([ad]{3})\s*/\s*([ad]{3})$')
rx8 = re.compile('([ad]\s*/\s*[ad]\s*/\s*[ad])$')
rx9 = re.compile('([ad]\s*-\s*[ad]\s*-\s*[ad])$')
rx10 = re.compile('\|?([ad]\s*\|\s*[ad]\s*\|\s*[ad])\|?$')
rx11 = re.compile('([ad]{3})\s*([ad]{3})$')
rx12 = re.compile('([ad]{3})\s*-\s*([ad]{3})$')
rx13 = re.compile('([ad]{3}),?\s*([ad]{3}),?\s*([ad]{3})$')
rx14 = re.compile('([ad]{3})\s*/\s*([ad]{3})\s*/\s*([ad]{3})$')
rx15 = re.compile('([ad]{3})\s*-\s*([ad]{3})\s*-\s*([ad]{3})$')
rx16 = re.compile('(\[[ad]\]\s*\[[ad]\]\s*\[[ad]\])$')
rx17 = re.compile('([ad]{4})$')

sparsregex.append(rx0)
sparsregex.append(rx1)
sparsregex.append(rx2)
sparsregex.append(rx3)
sparsregex.append(rx4)
sparsregex.append(rx5)
sparsregex.append(rx6)
sparsregex.append(rx7)
sparsregex.append(rx8)
sparsregex.append(rx9)
sparsregex.append(rx10)
sparsregex.append(rx11)
sparsregex.append(rx12)
sparsregex.append(rx13)
sparsregex.append(rx14)
sparsregex.append(rx15)
sparsregex.append(rx16)
sparsregex.append(rx17)

sparscounter = collections.Counter()

total = 0

for i in open(sparsfilename, 'r'):
    if not i.startswith('SPARS'):
       continue
    total += 1
    sparscomponent = i.strip()[6:].rsplit(' ', 1)[0].strip().lower()
    for s in seps:
        sparscomponent = sparscomponent.replace(s, '')
    sparsfound = False
    for rx in sparsregex:
        res = rx.match(sparscomponent)
        if res is not None:
            newres = []
            for n in res.groups():
                n = n.replace(' ', '')
                n = n.replace('|', '')
                n = n.replace('-', '')
                n = n.replace('/', '')
                n = n.replace('[', '')
                n = n.replace(']', '')
                newres.append(n)
            sparscounter.update(newres)
            sparsfound = True
            break
    if not sparsfound:
        print(sparscomponent)

for i in sparscounter.most_common():
    print(i)

print(total)
