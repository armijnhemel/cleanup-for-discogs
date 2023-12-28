#/usr/bin/env python3

# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright Armijn Hemel


import collections
import re

spars_filename = "dl.txt"
seps = ['.', '·', '•', '∙']

sparsregex = []
rx0 = re.compile(r'([ad]\s*[ad]\s*[ad])$')
rx1 = re.compile(r'\[([ad]{3})\]$')
rx2 = re.compile(r'([ad]{3}),\s*([ad]{3})$')
rx3 = re.compile(r'([ad]{3})\s*/\s*([ad]{3})$')
rx4 = re.compile(r'([ad]{3})\s*&\s*([ad]{3})$')
rx5 = re.compile(r'([ad]{3})\s*\|\s*([ad]{3})$')
rx6 = re.compile(r'([ad]{3})\s*\+\s*([ad]{3})$')
rx7 = re.compile(r'([ad]{3})\s*/\s*([ad]{3})$')
rx8 = re.compile(r'([ad]\s*/\s*[ad]\s*/\s*[ad])$')
rx9 = re.compile(r'([ad]\s*-\s*[ad]\s*-\s*[ad])$')
rx10 = re.compile(r'\|?([ad]\s*\|\s*[ad]\s*\|\s*[ad])\|?$')
rx11 = re.compile(r'([ad]{3})\s*([ad]{3})$')
rx12 = re.compile(r'([ad]{3})\s*-\s*([ad]{3})$')
rx13 = re.compile(r'([ad]{3}),?\s*([ad]{3}),?\s*([ad]{3})$')
rx14 = re.compile(r'([ad]{3})\s*/\s*([ad]{3})\s*/\s*([ad]{3})$')
rx15 = re.compile(r'([ad]{3})\s*-\s*([ad]{3})\s*-\s*([ad]{3})$')
rx16 = re.compile(r'(\[[ad]\]\s*\[[ad]\]\s*\[[ad]\])$')
rx17 = re.compile(r'([ad]{4})$')

for i in [rx0, rx1, rx2, rx3, rx4, rx5, rx6,
          rx7, rx8, rx9, rx10, rx11, rx12, rx13,
          rx14, rx15, rx16, rx17]:
    sparsregex.append(i)

spars_counter = collections.Counter()

total = 0

for i in open(spars_filename, 'r'):
    if not i.startswith('SPARS'):
        continue
    total += 1
    spars_component = i.strip()[6:].rsplit(' ', 1)[0].strip().lower()
    for s in seps:
        spars_component = spars_component.replace(s, '')
    spars_found = False
    for rx in sparsregex:
        res = rx.match(spars_component)
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
            spars_counter.update(newres)
            spars_found = True
            break
    if not spars_found:
        print(spars_component)

for i in spars_counter.most_common():
    print(i)

print(total)
