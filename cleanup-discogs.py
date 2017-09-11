#!/usr/bin/env python3

## Tool to discover 'smells' in the Discogs data dump. It prints a list of URLs
## of releases that need to be fixed.
## 
## Why this happens:
##
## https://www.well.com/~doctorow/metacrap.htm
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
## * hyperlinks :: in older releases it was OK to have normal HTML hyperlinks
###  but these have been replaced by markup:
##   https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-
##   There are still many releases where old hyperlinks are used.
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
## First the most common ones
depositores.append(re.compile(u'de?s?p*ós*i?r?tl?o?i?\s*l+e?g?al?\.?'))
depositores.append(re.compile(u'des?p?os+ito?\s+legt?al?\.?'))
depositores.append(re.compile(u'legal? des?posit'))
depositores.append(re.compile(u'dip. legal'))
depositores.append(re.compile(u'dip. leg.'))
depositores.append(re.compile(u'dipòsit legal'))
depositores.append(re.compile(u'dipósit legal'))

## then a slew of misspellings and variants
depositores.append(re.compile(u'deposito légal'))
depositores.append(re.compile(u'deposito legál'))
depositores.append(re.compile(u'depósito legl'))
depositores.append(re.compile(u'depósito lgeal'))
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
depositores.append(re.compile(u'depñosito legal'))
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
depositores.append(re.compile(u'depôsito legal'))
depositores.append(re.compile(u'depỏsito legal'))
depositores.append(re.compile(u'dep\'osito legal'))
depositores.append(re.compile(u'legal? des?posit'))
depositores.append(re.compile(u'legak des?posit'))
depositores.append(re.compile(u'legai des?posit'))
depositores.append(re.compile(u'legal depos?t'))
depositores.append(re.compile(u'legal dep\.'))

## deposito values, does not capture everything
depositovalre = re.compile(u'[abcmovz][\s\.\-/_]\s*\d{2}\.?\d{3}\s*[\-\./_]\s*(?:19|20)?\d{2}')

## label code
labelcodere = re.compile(u'\s*(?:lc)?\s*[\-/]?\s*\d{4,5}')

## https://en.wikipedia.org/wiki/SPARS_code
## also include 4 letter code, even though not officially a SPARS code
## Some people use "Sony distribution codes" in the SPARS field:
## https://www.discogs.com/forum/thread/339244
validsparscodes = set(['AAD', 'ADD', 'DDD', 'DAD', 'DDDD', 'DDAD'])

## a few rights societies from https://www.discogs.com/help/submission-guidelines-release-country.html
rights_societies = ['SGAE', 'BIEM', 'GEMA', 'STEMRA', 'SIAE', 'SABAM', 'SUISA']

class discogs_handler(xml.sax.ContentHandler):
	def __init__(self, config_settings):
		self.incountry = False
		self.inreleased = False
		self.inspars = False
		self.indeposito = False
		self.inlabelcode = False
		self.inbarcode = False
		self.inrightssociety = False
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
		self.inlabelcode = False
		self.inbarcode = False
		self.inrightssociety = False
		self.indeposito = False
		self.innotes = False
		if name == "release":
			## new release entry, so reset the isrejected field
			self.isrejected = False
			self.isdraft = False
			self.isdeleted = False
			self.debugcount += 1
			for (k,v) in attrs.items():
				if k == 'id':
					self.release = v
				elif k == 'status':
					if v == 'Rejected':
						self.isrejected = True
					elif v == 'Draft':
						self.isdraft = True
					elif v == 'Deleted':
						self.isdeleted = True
			return
		if self.isrejected or self.isdraft or self.isdeleted:
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
					elif v == 'Depósito Legal':
						self.indeposito = True
					elif v == 'Label Code':
						self.inlabelcode = True
					elif v == 'Rights Society':
						self.inrightssociety = True
					elif v == 'Barcode':
						self.inbarcode = True
				elif k == 'value':
					if not self.config['reportall']:
						if self.prev == self.release:
							continue
					if self.inspars:
						if self.config['check_spars_code']:
							## TODO: check if the format is actually a CD
							if not v in validsparscodes:
								self.count += 1
								self.prev = self.release
								print('%8d -- SPARS Code (format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					elif self.inlabelcode:
						if self.config['check_label_code']:
							if labelcodere.match(v.lower()) == None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Label Code (value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					elif self.inrightssociety:
						if self.config['check_label_code']:
							if v.startswith('LC'):
								self.count += 1
								self.prev = self.release
								print('%8d -- Label Code (in Rights Society): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					elif self.inbarcode:
						if self.config['check_label_code']:
							if v.lower().startswith('lc'):
								if labelcodere.match(v.lower()) != None:
									self.count += 1
									self.prev = self.release
									print('%8d -- Label Code (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						if self.country == 'Spain':
							if self.config['check_deposito']:
								if depositovalre.match(v.lower()) != None:
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						if self.config['check_rights_society']:
							for r in rights_societies:
								if v.replace('.', '') == r:
									self.count += 1
									self.prev = self.release
									print('%8d -- Rights Society (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									break
					if not self.indeposito:
						if self.country == 'Spain':
							if self.config['check_deposito']:
								if v.startswith("Depósito"):
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								elif v.startswith("D.L."):
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					else:
						if self.country == 'Spain':
							if self.config['check_deposito']:
								if v.endswith('.'):
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (formatting): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
				elif k == 'description':
					if not self.config['reportall']:
						if self.prev == self.release:
							continue
					self.description = v.lower()
					if self.config['check_rights_society']:
						if self.description in ["rights society", "rights societies", "right society"]:
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
						if self.description == "labelcode":
							self.count += 1
							self.prev = self.release
							print('%8d -- Label Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_spars_code']:
						if self.description == "spars code":
							self.count += 1
							self.prev = self.release
							print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							continue
					if self.config['check_isrc']:
						if self.description.startswith('isrc'):
							self.count += 1
							self.prev = self.release
							print('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
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
					if self.country == 'Spain':
						if self.config['check_deposito']:
							found = False
							if v == 'Depósito Legal':
								found = True
							else:
								for d in depositores:
									result = d.search(self.description)
									if result != None:
										found = True
										break
							## sometimes the depósito value itself can be found in the free text field
							if not found:
								deposres = depositovalre.match(self.description)
								if deposres != None:
									found = True

							if found:
								self.count += 1
								self.prev = self.release
								print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								continue

							## debug code to print descriptions that were skipped.
							## Useful to find misspellings of "depósito legal"
							if self.config['debug']:
								print(self.description, self.release)
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
				if self.config['check_deposito']:
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
			if self.config['check_html']:
				## see https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-
				if '&lt;a href="http://www.discogs.com/release/' in content.lower():
					self.count += 1
					print('%8d -- old link (Notes): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
			if self.config['check_url']:
				if '[url=http://www.discogs.com/release/' in content.lower():
					self.count += 1
					print('%8d -- URL (Notes): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
		sys.stdout.flush()

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
				if config.get(section, 'isrc') == 'yes':
					check_isrc = True
				else:
					check_isrc = False
			except Exception:
				check_isrc = True
			config_settings['check_isrc'] = check_isrc

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

			try:
				if config.get(section, 'html') == 'yes':
					check_html = True
				else:
					check_html = False
			except Exception:
				check_html = True
			config_settings['check_html'] = check_html

			try:
				if config.get(section, 'url') == 'yes':
					check_url = True
				else:
					check_url = False
			except Exception:
				check_url = False
			config_settings['check_url'] = check_url

			## month is 00 check: default is False
			try:
				if config.get(section, 'month') == 'yes':
					check_month = True
				else:
					check_month = False
			except Exception:
				check_month = True
			config_settings['check_month'] = check_month

			## reporting all: default is False
			try:
				if config.get(section, 'reportall') == 'yes':
					reportall = True
				else:
					reportall = False
			except Exception:
				reportall = True
			config_settings['reportall'] = reportall

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
