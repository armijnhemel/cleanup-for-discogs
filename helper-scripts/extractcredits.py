## Helper script to grab the credits list from the Discogs creditslist
## https://www.discogs.com/help/creditslist
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017 - Armijn Hemel

creditslines = open('credits2', 'r')
counter = 0
for i in creditslines:
	if (counter % 5) == 0:
		print(i.strip()[4:-5])
	counter += 1
