#!/usr/bin/env python3

# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright Armijn Hemel


import collections
import re

label_filename = "label.txt"

label_regex = []
rx0 = re.compile(r'(?:lc)[\s/\-]*(\d{4,6})')

label_regex.append(rx0)

label_counter = collections.Counter()

total = 0
valid = 0
ignored = 0

with open(label_filename, 'r') as label_file:
    for i in label_file:
        if not i.startswith('LABEL CODE'):
            continue
        total += 1
        label_component = i.strip()[10:].strip().lower()
        label_code_found = False
        for rx in label_regex:
            res = rx.match(label_component)
            if res is not None:
                label_code = res.groups()[0]
                if len(label_code) == 4:
                    label_code = "00" + label_code
                elif len(label_code) == 5:
                    label_code = "0" + label_code
                label_counter.update([label_code])
                label_code_found = True
                break
        if label_code_found:
            valid += 1
        else:
            ignored += 1

print(f"TOTAL: {total}")
print(f"VALID: {valid}")
print(f"IGNORED: {ignored}")
print(f"Labels: {len(label_counter)}")

counter = 1
for label, amount in label_counter.most_common():
    print(f"{counter} LC {label}: {amount}")
    counter += 1
