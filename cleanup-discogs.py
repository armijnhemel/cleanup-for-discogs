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

## basque: http://www.euskadi.eus/deposito-legal/web01-a2libzer/es/impresion.html
depositores.append(re.compile(u'l\.g\.'))

depositovalres = []
## deposito values, probably does not capture everything
depositovalres.append(re.compile(u'[abcjlmopstvz][\s\.\-/_:]\s*\d{0,2}\.?\d{2,3}\s*[\-\./_]\s*(?:19|20)?\d{2}'))
depositovalres.append(re.compile(u'(?:ab|al|as|av|ba|bi|bu|cc|ca|co|cr|cs|gc|gi|gr|gu|hu|le|lr|lu|ma|mu|na|or|pm|po|sa|se|sg|so|ss|s\.\s.|te|tf|t\.f\.|to|va|vi|za)[\s\.\-/_:]\s*\d{0,2}\.?\d{2,3}\s*[\-\./_]\s*(?:19|20)?\d{2}'))

## label code
#labelcodere = re.compile(u'\s*(?:lc)?\s*[\-/]?\s*\d{4,5}')
labelcodere = re.compile(u'\s*(?:lc)?\s*[\-/]?\s*\d{4,5}$')

## https://en.wikipedia.org/wiki/SPARS_code
## also include 4 letter code, even though not officially a SPARS code
## Some people use "Sony distribution codes" in the SPARS field:
## https://www.discogs.com/forum/thread/339244
validsparscodes = set(['aaa', 'aad', 'add', 'ada', 'daa', 'ddd', 'dad', 'dda', 'dddd', 'ddad'])

spars_ftf = set(["spars code", "spar code", "spars-code", "spare code",
"sparse code", "sparc code", "spars.code", "sparcs", "sparsc code",
"spard code", "sparks code", "sparrs code", "sparscode", "sparce code",
"saprs-code", "saprs code", "sars code", "sprs code", "spas code",
"pars code", "spars  code", "sparr code", "sparts code", "spras code",
"spars cod", "spars cde", "spars cpde", "spars cods", "spars codde", "spars ccde"
"spars coe", "spars coce", "spars coda", "spars"])

label_code_ftf = set(['label code', 'labelcode', 'lbel code', 'laabel code'])

isrc_ftf = set(['international standard recording code','international standard recording copyright', 'international standart recording code', 'isrc', 'irsc', 'iscr', 'international standard code recording'])

## a few rights societies from https://www.discogs.com/help/submission-guidelines-release-country.html
rights_societies = ['SGAE', 'BIEM', 'GEMA', 'STEMRA', 'SIAE', 'SABAM', 'SUISA', 'ASCAP', 'BMI', 'JASRAC', 'AEPI', 'OSA', 'SOKOJ', 'SOCAN', 'NCB']

class discogs_handler(xml.sax.ContentHandler):
	def __init__(self, config_settings):
		self.incountry = False
		self.inreleased = False
		self.inspars = False
		self.inother = False
		self.indeposito = False
		self.inlabelcode = False
		self.inbarcode = False
		self.inasin = False
		self.inisrc = False
		self.inrightssociety = False
		self.intracklist = False
		self.innotes = False
		self.release = None
		self.country = None
		self.indescription = False
		self.indescriptions = False
		self.debugcount = 0
		self.count = 0
		self.prev = None
		self.formattexts = []
		self.iscd = False
		self.isrejected = False
		self.isdraft = False
		self.isdeleted = False
		self.depositofound = False
		self.config = config_settings
		self.contentbuffer = ''
	def startElement(self, name, attrs):
		## first process the contentbuffer
		if self.incountry:
			self.country = self.contentbuffer
		elif self.indescription:
			if self.indescriptions:
				if 'Styrene' in self.contentbuffer:
					pass
		elif self.inreleased:
			if self.config['check_month']:
				if '-00-' in self.contentbuffer:
					self.count += 1
					print('%8d -- Month 00: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					sys.stdout.flush()
			if self.config['check_year']:
				if self.contentbuffer != '':
					try:
						self.year = int(self.contentbuffer.split('-', 1)[0])
					except:
						print('%8d -- Year \'%s\' invalid: https://www.discogs.com/release/%s' % (self.count, self.contentbuffer, str(self.release)))
						sys.stdout.flush()
		elif self.innotes:
			if '카지노' in self.contentbuffer:
				## Korean casino spam that pops up every once in a while
				print('Spam: https://www.discogs.com/release/%s' % str(self.release))
				sys.stdout.flush()
			if self.country == 'Spain':
				if self.config['check_deposito'] and not self.depositofound:
					## sometimes "deposito legal" can be found in the "notes" section
					content_lower = self.contentbuffer.lower()
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
				if '&lt;a href="http://www.discogs.com/release/' in self.contentbuffer.lower():
					self.count += 1
					print('%8d -- old link (Notes): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
		sys.stdout.flush()

		## now reset some values
		self.incountry = False
		self.inreleased = False
		self.inspars = False
		self.inother = False
		self.inlabelcode = False
		self.inbarcode = False
		self.inasin = False
		self.inisrc = False
		self.inrightssociety = False
		self.indeposito = False
		self.innotes = False
		self.indescription = False
		self.intracklist = False
		self.contentbuffer = ''
		if name == "release":
			## new release entry, so reset the isrejected field
			self.isrejected = False
			self.isdraft = False
			self.isdeleted = False
			self.depositofound = False
			self.seentracklist = False
			self.debugcount += 1
			self.iscd = False
			self.year = None
			self.formattexts = []
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
		if name == 'descriptions':
			self.indescriptions = True
		elif not name == 'description':
			self.indescriptions = False

		if name == 'country':
			self.incountry = True
		elif name == 'label':
			for (k,v) in attrs.items():
				if k == 'catno':
					catno = v.lower()
					if self.config['check_label_code']:
						if catno.startswith('lc'):
							if labelcodere.match(catno) != None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Possible Label Code (in Catalogue Number): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					if self.config['check_deposito']:
						## now check for D.L.
						dlfound = False
						for d in depositores:
							result = d.search(catno)
							if result != None:
								for depositovalre in depositovalres:
									if depositovalre.search(catno) != None:
										dlfound = True
										break

						if dlfound:
							self.count += 1
							self.prev = self.release
							print('%8d -- Possible Depósito Legal (in Catalogue Number): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
		elif name == 'tracklist':
			self.intracklist = True
		elif name == 'format':
			for (k,v) in attrs.items():
				if k == 'name':
					if v == 'CD':
						self.iscd = True
				elif k == 'text':
					if v != '':
						if self.config['check_spars_code']:
							if v.lower() in validsparscodes:
								self.count += 1
								self.prev = self.release
								print('%8d -- Possible SPARS Code (in Format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
		elif name == 'description':
			self.indescription = True
		elif name == 'released':
			self.inreleased = True
		elif name == 'notes':
			self.innotes = True
		elif name == 'identifier':
			isdeposito = False
			attritems = dict(attrs.items())
			if 'type' in attritems:
				v = attritems['type']
				if v == 'SPARS Code':
					self.inspars = True
				elif v == 'Depósito Legal':
					self.indeposito = True
					self.depositofound = True
				elif v == 'Label Code':
					self.inlabelcode = True
				elif v == 'Rights Society':
					self.inrightssociety = True
				elif v == 'Barcode':
					self.inbarcode = True
				elif v == 'ASIN':
					self.inasin = True
				elif v == 'ISRC':
					self.inisrc = True
				elif v == 'Other':
					self.inother = True
			if 'value' in attritems:
				v = attritems['value']
				if not self.config['reportall']:
					if self.prev == self.release:
						return
				if self.inspars:
					if self.config['check_spars_code']:
						## TODO: check if the format is actually a CD or CD-like medium
						#if not self.iscd:
						#	print("SPARS (No CD): https://www.discogs.com/release/%s --" % str(self.release), str(self.release))
						#	self.count += 1
						#	self.prev = self.release
						if v == "none":
							return
						## Sony format codes
						## https://www.discogs.com/forum/thread/339244
						## https://www.discogs.com/forum/thread/358285
						if v == 'CDC' or v == 'CDM':
							self.count += 1
							self.prev = self.release
							print('%8d -- Sony Format Code in SPARS: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						wrongspars = False
						tmpspars = v.lower().strip()
						for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
							tmpspars = tmpspars.replace(s, '')
						if not tmpspars in validsparscodes:
							wrongspars = True

						if wrongspars:
							self.count += 1
							self.prev = self.release
							print('%8d -- SPARS Code (format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				elif not self.inother:
					if self.config['check_spars_code']:
						if v.lower() in validsparscodes:
							self.count += 1
							self.prev = self.release
							print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if 'd' in v.lower():
							## just check a few other possibilities of possible SPARS codes
							if v.lower().replace(' ', '') in validsparscodes:
								self.count += 1
								self.prev = self.release
								print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
							if v.lower().replace('.', '') in validsparscodes:
								self.count += 1
								self.prev = self.release
								print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
				if self.inlabelcode:
					if self.config['check_label_code']:
						## check how many people use 'O' instead of '0'
						if v.lower().startswith('lc'):
							if 'O' in v:
								print('%8d -- Spelling error in Label Code): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								sys.stdout.flush()
						if labelcodere.match(v.lower()) == None:
							self.count += 1
							self.prev = self.release
							print('%8d -- Label Code (value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				if self.inrightssociety:
					if self.config['check_label_code']:
						if v.lower().startswith('lc'):
							if labelcodere.match(v.lower()) != None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Label Code (in Rights Society): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					if self.config['check_rights_society']:
						pass
				elif not self.inother:
					if self.config['check_rights_society']:
						for r in rights_societies:
							if v.replace('.', '') == r or v.replace(' ', '') == r:
								self.count += 1
								self.prev = self.release
								print('%8d -- Rights Society (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								break
				if self.inbarcode:
					if self.config['check_label_code']:
						if v.lower().startswith('lc'):
							if labelcodere.match(v.lower()) != None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Label Code (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					if self.country == 'Spain':
						if self.config['check_deposito'] and not self.depositofound:
							for depositovalre in depositovalres:
								if depositovalre.match(v.lower()) != None:
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									return
					if self.config['check_rights_society']:
						for r in rights_societies:
							if v.replace('.', '') == r or v.replace(' ', '') == r:
								self.count += 1
								self.prev = self.release
								print('%8d -- Rights Society (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								break
				if self.inasin:
					if not len(v.split(':')[-1].strip()) == 10:
						self.count += 1
						self.prev = self.release
						print('%8d -- ASIN (wrong length): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						sys.stdout.flush()
						return
				if self.inisrc:
					if self.config['check_isrc']:
						## Check the length of ISRC fields. According to the specifications these should
						## be 12 in length. Some ISRC identifiers that have been recorded in the database
						## cover a range of tracks. These will be reported as wrong ISRC codes. It is unclear
						## what needs to be done with those.
						## first get rid of cruft
						isrc_tmp = v.strip().upper()
						if isrc_tmp.startswith('ISRC'):
							isrc_tmp = isrc_tmp.split('ISRC')[-1].strip()
						if isrc_tmp.startswith('CODE'):
							isrc_tmp = isrc_tmp.split('CODE')[-1].strip()
						## replace a few characters
						isrc_tmp = isrc_tmp.replace('-', '')
						isrc_tmp = isrc_tmp.replace(' ', '')
						isrc_tmp = isrc_tmp.replace('.', '')
						isrc_tmp = isrc_tmp.replace(':', '')
						isrc_tmp = isrc_tmp.replace('–', '')
						if not len(isrc_tmp) == 12:
							self.count += 1
							self.prev = self.release
							print('%8d -- ISRC (wrong length): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							sys.stdout.flush()
							return
				if not self.indeposito:
					if self.country == 'Spain':
						if self.config['check_deposito']:
							if v.startswith("Depósito"):
								self.count += 1
								self.prev = self.release
								print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
							elif v.startswith("D.L."):
								self.count += 1
								self.prev = self.release
								print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
				else:
					if self.country == 'Spain':
						if self.config['check_deposito']:
							if v.endswith('.'):
								self.count += 1
								self.prev = self.release
								print('%8d -- Depósito Legal (formatting): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
							if self.year != None:
								## now try to find the year
								depositoyear = None
								if v.strip().endswith('℗'):
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (formatting, has ℗): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									## ugly hack, remove ℗ to make at least be able to do some sort of check
									v = v.strip().rsplit('℗', 1)[0]
								## several separators, including some Unicode ones
								for sep in ['-', '–', '/', '.', ' ', '\'', '_']:
									try:
										depositoyeartext = v.strip().rsplit(sep, 1)[-1]
										if sep == '.' and len(depositoyeartext) == 3:
											continue
										if '.' in depositoyeartext:
											depositoyeartext = depositoyeartext.replace('.', '')
										depositoyear = int(depositoyeartext)
										if depositoyear < 100:
											if depositoyear <= 17:
												depositoyear += 2000
											else:
												depositoyear += 1900
										break
									except:
										pass

								## TODO, also allow (year), example: https://www.discogs.com/release/265497
								if depositoyear != None:
									if depositoyear < 1900:
										self.count += 1
										self.prev = self.release
										print("%8d -- Depósito Legal (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif depositoyear > 2017:
										self.count += 1
										self.prev = self.release
										print("%8d -- Depósito Legal (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif self.year < depositoyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Depósito Legal (release date earlier): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
								else:
									self.count += 1
									self.prev = self.release
									print("%8d -- Depósito Legal (year not found): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
								sys.stdout.flush()
			if 'description' in attritems:
				v = attritems['description']
				if not self.config['reportall']:
					if self.prev == self.release:
						return
				self.description = v.lower()
				if self.config['check_rights_society']:
					if self.description in ["rights society", "rights societies", "right society", "mechanical rights society"]:
						self.count += 1
						self.prev = self.release
						print('%8d -- Rights Society: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.config['check_label_code']:
					if self.description in label_code_ftf:
						self.count += 1
						self.prev = self.release
						print('%8d -- Label Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.config['check_spars_code']:
					if not self.inspars:
						sparsfound = False
						for spars in spars_ftf:
							if spars in self.description:
								sparsfound = True
								self.count += 1
								self.prev = self.release
								print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								break
						if sparsfound:
							return
				if self.config['check_asin']:
					if not self.inasin and self.description.startswith('asin'):
						self.count += 1
						self.prev = self.release
						print('%8d -- ASIN (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.config['check_isrc']:
					if self.description.startswith('isrc'):
						self.count += 1
						self.prev = self.release
						print('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
					if self.description.startswith('issrc'):
						self.count += 1
						self.prev = self.release
						print('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
					for isrc in isrc_ftf:
						if isrc in self.description:
							self.count += 1
							self.prev = self.release
							print('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				if self.config['check_mastering_sid']:
					if self.description == "mastering sid code":
						self.count += 1
						self.prev = self.release
						print('%8d -- Mastering SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.config['check_mould_sid']:
					if self.description == "mould sid code":
						self.count += 1
						self.prev = self.release
						print('%8d -- Mould SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.country == 'Spain':
					if self.config['check_deposito'] and not self.indeposito:
						found = False
						for d in depositores:
							result = d.search(self.description)
							if result != None:
								found = True
								break

						## sometimes the depósito value itself can be found in the free text field
						if not found:
							for depositovalre in depositovalres:
								deposres = depositovalre.match(self.description)
								if deposres != None:
									found = True
									break

						if found:
							self.count += 1
							self.prev = self.release
							print('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return

						## debug code to print descriptions that were skipped.
						## Useful to find misspellings of "depósito legal"
						if self.config['debug']:
							print(self.description, self.release)
				sys.stdout.flush()

	def characters(self, content):
		self.contentbuffer += content

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
				if config.get(section, 'asin') == 'yes':
					check_asin = True
				else:
					check_asin = False
			except Exception:
				check_asin = True
			config_settings['check_asin'] = check_asin

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


			## month is 00 check: default is False
			try:
				if config.get(section, 'month') == 'yes':
					check_month = True
				else:
					check_month = False
			except Exception:
				check_month = False
			config_settings['check_month'] = check_month

			## year is wrong check: default is False
			try:
				if config.get(section, 'year') == 'yes':
					check_year = True
				else:
					check_year = False
			except Exception:
				check_year = False
			config_settings['check_year'] = check_year
			## reporting all: default is False
			try:
				if config.get(section, 'reportall') == 'yes':
					reportall = True
				else:
					reportall = False
			except Exception:
				reportall = False
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
