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
##   but this is no longer allowed. When editing an entry that has 00 as the
##   month Discogs will throw an error.
## 
## The results that are printed by this script are by no means complete.
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017 - Armijn Hemel

import xml.sax
import sys, os, gzip, re
import argparse, configparser

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
depositores.append(re.compile(u'depásito legal'))
depositores.append(re.compile(u'legal deposit'))

class discogs_handler(xml.sax.ContentHandler):
	def __init__(self, config_settings):
		self.incountry = False
		self.inreleased = False
		self.inspars = False
		self.innotes = False
		self.release = None
		self.country = None
		self.debugcount = 0
		self.count = 0
		self.prev = None
		self.isrejected = False
		self.config = config_settings
	def startElement(self, name, attrs):
		self.incountry = False
		self.inreleased = False
		self.inspars = False
		self.innotes = False
		if self.config['debug']:
			if self.debugcount == 300000:
				sys.exit()
		if name == "release":
			## new release entry, so reset the isrejected field
			self.isrejected = False
			self.debugcount += 1
			for (k,v) in attrs.items():
				if k == 'id':
					self.release = v
				elif k == 'status':
					if v == 'Rejected':
						self.isrejected = True
			return
		if self.isrejected:
			return
		if name == 'country':
			self.incountry = True
		elif name == 'released':
			self.inreleased = True
		elif name == 'notes':
			self.innotes = True
		elif name == 'identifier':
			isdeposito = False
			for (k,v) in attrs.items():
				if k == 'type':
					if v == 'SPARS Code':
						self.inspars = True
					pass
				elif k == 'value':
					if self.inspars:
						## check SPARS code here
						pass
				elif k == 'description':
					if self.prev == self.release:
						continue
					self.description = v.lower()
					if self.config['check_rights_society']:
						if self.description == "rights society":
							self.count += 1
							self.prev = self.release
							print('%8d -- Rights Society: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_label_code']:
						if self.description == "label code":
							self.count += 1
							self.prev = self.release
							print('%8d -- Label Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_spars_code']:
						if self.description == "spars code":
							self.count += 1
							self.prev = self.release
							print('%8d -- SPARS Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_mastering_sid']:
						if self.description == "mastering sid code":
							self.count += 1
							self.prev = self.release
							print('%8d -- Mastering SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_mould_sid']:
						if self.description == "mould sid code":
							self.count += 1
							self.prev = self.release
							print('%8d -- Mould SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_deposito']:
						if self.country == 'Spain':
							found = False
							for d in depositores:
								result = d.search(self.description)
								if result != None:
									self.count += 1
									found = True
									self.prev = self.release
									print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									break
							## debug code to print descriptions that were skipped.
							## Useful to find misspellings of "depósito legal"
							if self.config['debug']:
								if not found:
									pass
									#print(self.description, self.release)
					sys.stdout.flush()
	def characters(self, content):
		if self.incountry:
			self.country = content
		elif self.inreleased:
			if self.config['check_month']:
				if '-00-' in content:
					self.count += 1
					print('%8d -- Month 00: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					sys.stdout.flush()
		elif self.innotes:
			if self.country == 'Spain':
				## sometimes "deposito legal" can be found in the "notes" section
				content_lower = content.lower()
				for d in depositores:
					result = d.search(content_lower)
					if result != None:
						self.count += 1
						found = True
						self.prev = self.release
						print('%8d -- Depósito Legal (Notes): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						break

def main(argv):
	parser = argparse.ArgumentParser()

	## the following options are provided on the commandline
	parser.add_argument("-c", "--config", action="store", dest="cfg", help="path to configuration file", metavar="FILE")
	parser.add_argument("-d", "--datadump", action="store", dest="datadump", help="path to discogs data dump", metavar="DATA")
	args = parser.parse_args()

	## path of the gzip compressed releases file
	if args.datadump == None:
		parser.error("Data dump file missing")

	if not os.path.exists(args.datadump):
		parser.error("Data dump file does not exist")

	if not os.path.isfile(args.datadump):
		parser.error("Data dump file is not a file")

	if args.cfg == None:
		parser.error("Configuration file missing")

	if not os.path.exists(args.cfg):
		parser.error("Configuration file does not exist")

	config = configparser.ConfigParser()

	configfile = open(args.cfg, 'r')

	try:
		config.readfp(configfile)
	except Exception:
		print("Cannot read configuration file", file=sys.stderr)
		sys.exit(1)

	config_settings = {}

	for section in config.sections():
		if section == 'cleanup':
			try:
				if config.get(section, 'deposito') == 'yes':
					check_deposito = True
				else:
					check_deposito = False
			except Exception:
				check_deposito = True
			config_settings['check_deposito'] = check_deposito

			try:
				if config.get(section, 'rights_society') == 'yes':
					check_rights_society = True
				else:
					check_rights_society = False
			except Exception:
				check_rights_society = True
			config_settings['check_rights_society'] = check_rights_society

			try:
				if config.get(section, 'label_code') == 'yes':
					check_label_code = True
				else:
					check_label_code = False
			except Exception:
				check_label_code = True
			config_settings['check_label_code'] = check_label_code

			try:
				if config.get(section, 'mastering_sid') == 'yes':
					check_mastering_sid = True
				else:
					check_mastering_sid = False
			except Exception:
				check_mastering_sid = True
			config_settings['check_mastering_sid'] = check_mastering_sid

			try:
				if config.get(section, 'mould_sid') == 'yes':
					check_mould_sid = True
				else:
					check_mould_sid = False
			except Exception:
				check_mould_sid = True
			config_settings['check_mould_sid'] = check_mould_sid

			try:
				if config.get(section, 'spars') == 'yes':
					check_spars = True
				else:
					check_spars = False
			except Exception:
				check_spars = True
			config_settings['check_spars_code'] = check_spars

			## month is 00 check: default is False
			try:
				if config.get(section, 'month') == 'yes':
					check_month = True
				else:
					check_month = False
			except Exception:
				check_month = True
			config_settings['check_month'] = check_month

			## debug: default is False
			try:
				if config.get(section, 'debug') == 'yes':
					debug = True
				else:
					debug = False
			except Exception:
				debug = False
			config_settings['debug'] = debug

	configfile.close()

	parser = xml.sax.make_parser()
	parser.setContentHandler(discogs_handler(config_settings))
	try:
		dumpfile = gzip.open(args.datadump, "rb")
	except Exception:
		print("Cannot open dump file", file=sys.stderr)
		sys.exit(1)
	parser.parse(dumpfile)

	dumpfile.close()

if __name__ == "__main__":
	main(sys.argv)
