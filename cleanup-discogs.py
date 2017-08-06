#!/usr/bin/env python3

## Tool to discover 'smells' in the Discogs data dump. It prints a list of URLs
## of releases that need to be fixed.
## 
## Currently the following smells can be discovered:
##
## * depósito legal :: until recently the "depósito legal" data (for Spanish
##   releases) was essentially free text in the "Barcode and Other Identifiers"
##   section.
##   Since the August 2017 dump there is a separate field for it (and it has
##   effectively become a first class citizen in BaOI), but there are still many
##   releases where this information has not been changed and is in an "Other"
##   field in BaOI.
##   Also, there are many misspellings, making it more difficult to find.
## * label code :: until recently "Other" was used to specify the
##   label code, but since then there is a dedicated field called
##   "Label Code". There are still many entries that haven't been changed
##   though.
## * SPARS code :: until recently "Other" was used to specify the
##   SPARS code, but since then there is a dedicated field called
##   "SPARS Code". There are still many entries that haven't been changed
##   though.
## * rights society :: until a few years ago "Other" was used to specify
##   the rights society, but since then there is a dedicated field called
##   "Rights Society". There are still many entries that haven't been changed
##   though.
## * month as 00 :: in older releases it was allowed to have the month as 00
##   but this is no longer allowed. When editing a file that has 00 as the
##   month Discogs will throw an error.
## 
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017 - Armijn Hemel

import xml.sax
import sys, os, gzip, re
import argparse

## path of the gzip compressed releases file
discogs_path = '/home/armijn/discogs-data/discogs_20170801_releases.xml.gz'

## a list to store the regular expression to recognize
## "depósito legal" in the BaOI 'Other' field
depositores = []

## a few variants of "depósito legal" found in the discogs datadump
## All regular expressions are lower case.
## These regular expressions can probably be made a bit simpler
depositores.append(re.compile(u'des?p?ós*itl?o?\s*le?gal?\.?'))
depositores.append(re.compile(u'des?posito legt?al\.?'))
depositores.append(re.compile(u'depodito legal\.?'))
depositores.append(re.compile(u'depòsito? legal\.?'))
depositores.append(re.compile(u'déposito legal\.?'))
depositores.append(re.compile(u'depós?tio legal\.?'))
depositores.append(re.compile(u'dep\.?\s*legal\.?'))
depositores.append(re.compile(u'd\.?\s*legal\.?'))
depositores.append(re.compile(u'de?pto\.?\s*legal\.?'))
depositores.append(re.compile(u'depótiso legal'))
depositores.append(re.compile(u'depósitio legal'))
depositores.append(re.compile(u'depósiti legal'))
depositores.append(re.compile(u'deposrito legal'))
depositores.append(re.compile(u'deoósito legal'))
depositores.append(re.compile(u'depóaito legal'))
depositores.append(re.compile(u'depõsito legal'))
depositores.append(re.compile(u'deposiro legal\.?'))
depositores.append(re.compile(u'depósito légal'))
depositores.append(re.compile(u'déposito légal'))
depositores.append(re.compile(u'd\.\s*l\.'))
depositores.append(re.compile(u'dep\.\s*leg\.'))
depositores.append(re.compile(u'dep.\s*l.'))
depositores.append(re.compile(u'deposito lagal'))
depositores.append(re.compile(u'depósito lagal'))
depositores.append(re.compile(u'depósito degal'))
depositores.append(re.compile(u'depósito leagal'))
depositores.append(re.compile(u'depóosito legal'))
depositores.append(re.compile(u'depósite legal'))
depositores.append(re.compile(u'sepósito legal'))
depositores.append(re.compile(u'deopósito legal'))

## some defaults
## TODO: make configurable
check_deposito = True
check_rights_society = True
check_label_code = True
check_mastering_sid = True
check_mould_sid = True
check_spars_code = True
debug = True

class discogs_handler(xml.sax.ContentHandler):
	def __init__(self):
		self.incountry = False
		self.inreleased = False
		self.release = None
		self.country = None
		self.debugcount = 0
		self.count = 0
		self.prev = None
	def startElement(self, name, attrs):
		self.incountry = False
		self.inreleased = False
		if debug:
			if self.debugcount == 300000:
				sys.exit()
		if name == "release":
			self.debugcount += 1
			for (k,v) in attrs.items():
				if k == 'id':
					self.release = v
					break
		elif name == 'country':
			self.incountry = True
		elif name == 'released':
			self.inreleased = True
		elif name == 'identifier':
			isdeposito = False
			for (k,v) in attrs.items():
				if k == 'description':
					if self.prev == self.release:
						continue
					self.description = v.lower()
					if check_rights_society:
						if self.description == "rights society":
							self.count += 1
							self.prev = self.release
							print('%8d -- Rights Society: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if check_label_code:
						if self.description == "label code":
							self.count += 1
							self.prev = self.release
							print('%8d -- Label Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if check_spars_code:
						if self.description == "spars code":
							self.count += 1
							self.prev = self.release
							print('%8d -- SPARS Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if check_mastering_sid:
						if self.description == "mastering sid code":
							self.count += 1
							self.prev = self.release
							print('%8d -- Mastering SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if check_mould_sid:
						if self.description == "mould sid code":
							self.count += 1
							self.prev = self.release
							print('%8d -- Mould SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if check_deposito:
						if self.country == 'Spain':
							found = False
							for d in depositores:
								result = d.search(self.description)
								if result != None:
									self.count += 1
									found = True
									self.prev = self.release
									print('%8d -- Depósito Legal: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									break
							## debug code to print descriptions that were skipped.
							## Useful to find misspellings of "depósito legal"
							if debug:
								if not found:
									pass
									#print(self.description, self.release)
					sys.stdout.flush()
	def characters(self, content):
		if self.incountry:
			self.country = content
		elif self.inreleased:
			## don't do anything right now because of the very large amount of results
			return
			if '-00-' in content:
				self.count += 1
				print('%8d -- Month 00: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
				sys.stdout.flush()

parser = xml.sax.make_parser()
parser.setContentHandler(discogs_handler())
parser.parse(gzip.open(discogs_path,"rb"))
