#!/usr/bin/python3

## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0-only
##
## Copyright 2018 - Armijn Hemel

import re

## first open the HTML file
#userfile = open('contributors?page=1', 'rb')

## use a concatenation of all HTML files grabbed from Discogs
userfile = open('contributors', 'rb')

seenfirstuser = False
needtd = False

total = 0
usertocontributions = []

for u in userfile:
	if b'class="linked_username"' in u:
		seenfirstuser = True
		needtd = True
		username = re.search(b"<a href=\"/user/(.*)\" class", u).groups()[0]
	## skip all needless lines
	if not seenfirstuser:
		continue
	if needtd:
		if not b'<td>' in u:
			continue
		needtd = False
		amount = int(re.search(b"<td>([\d,]+)</td>", u).groups()[0].replace(b',', b''))
		usertocontributions.append((username, amount))
		total+= amount

## finally close the file
userfile.close()

oldcounter = 0
counter = 0
localtotal = 0
accumulativetotal = 0
users = sorted(usertocontributions,key = lambda x: x[1], reverse=True)
for u in users:
	counter += 1
	#print(u[0].decode(), u[1], "{:.2%}".format((u[1]/total)))
	localtotal += u[1]
	if counter % 50 == 0:
		accumulativetotal += localtotal
		print()
		print("PERCENTAGE OF USERS: {:.2%}".format(counter/len(users)))
		print("PERCENTAGE PER BATCH %d-%d:" % (oldcounter+1, counter), "{:.2%}".format((localtotal/total)))
		print("ACCUMULATIVE %d-%d:" % (oldcounter+1, counter), "{:.2%}".format((accumulativetotal/total)))
		print()
		localtotal = 0
		oldcounter = counter
