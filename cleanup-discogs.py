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
import sys, os, gzip, re, datetime
import argparse, configparser

## grab the current year. Make sure to set the clock of your machine
## to the correct date or use NTP!
currentyear = datetime.datetime.utcnow().year

## a list to store the regular expression to recognize
## "depósito legal" in the BaOI 'Other' field
depositores = []

## a few variants of "depósito legal" found in the discogs datadump
## All regular expressions are lower case.
## First the most common ones
depositores.append(re.compile(u'depósito legal'))
depositores.append(re.compile(u'deposito legal'))
depositores.append(re.compile(u'de?s?p*ós*i?r?tl?o?i?\s*l+e?g?al?\.?'))
depositores.append(re.compile(u'des?p?os+ito?\s+legt?al?\.?'))
depositores.append(re.compile(u'legal? des?posit'))
depositores.append(re.compile(u'dep\.\s*legal'))
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

masteringsidre = re.compile(u'\s*(?:ifpi)?\s*l\w{3,4}$')
mouldsidre = re.compile(u'\s*(?:ifpi)?\s*\w{4,5}$')

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

isrc_ftf = set(['international standard recording code','international standard recording copyright', 'international standart recording code', 'isrc', 'irsc', 'iscr', 'international standard code recording', 'i.s.r.c.'])

## a few rights societies from https://www.discogs.com/help/submission-guidelines-release-country.html
rights_societies = set(["BIEM", "ACAM", "ACDAM", "ACUM ", "ADDAF", "AEPI", "AGADU", "AKKA/LAA", "AKM", "ALBAUTOR", "AMCOS", "APA", "APDASPAC", "APDAYC", "APRA", "ARTISJUS", "ASCAP", "AUSTROMECHANA", "BMI", "BUMA", "CAPAC", "CASH", "CEDAR", "CISAC", "CMRRA", "COTT", "EAU", "FCA", "FILSCAP", "GEMA", "GESAC", "GESAP", "GRAMO", "GVL", "HDS", "HFA", "IMRO", "IPRS", "JASRAC", "KCI", "KODA", "KOMCA", "LATGA-A", "MACP", "MECOLICO", "MCPS", "MCSC", "MCSK", "MESAM", "MUSICAUTOR", "MUST", "NCB", "n©b", "OSA", "PAMRA", "PPL", "PROCAN", "PRS", "RAO", "SABAM", "SACEM", "SACEM Luxembourg", "SACM", "SACVEN", "SADAIC", "SAMI", "SAMRO", "SAYCO", "SAZAS", "SBACEM", "SCPP", "SCD", "SDRM", "SEDRIM", "SENA", "SESAC", "SGA", "SGAE", "SIAE", "SOCAN", "SODRAC", "SOKOJ", "SOZA", "SPA", "STEF", "STEMRA", "STIM", "SUISA", "TEOSTO", "TONO", "UACRR", "UBC", "UCMR-ADA", "ZAIKS"])

rights_societies_ftf = set(["rights society", "rights societies", "right society", "mechanical rights society", "rights societiy", "rights societe", "rights societry", "rights societty", "rights societiers", "roghts society", "ritght society", "rigths society", "right society", "righty society", "rhights society", "righrs society", "righs society", "righst society"])

## SID codes spellings
## These are all exact matches, as too often there are descriptions, such as "near mastering SID code"
## or similar and using a regular expression would lead to many false positives.
## Some of these might seem exactly the same, such as 'mastering sid code' and 'mastering sid сode' but
## they are not, as the latter uses a Cyrillic 'с', sigh.
masteringsids = set(['mastering sid code', 'master sid code', 'master sid', 'masterung sid code', 'mastrering sid code', 'matering sid code', 'sid code mastering', 'sid code (mastering)', 'sid code: mastering','sid code [mastering]', '(sid code, mastering)', 'sid code, mastering', 'sid code - mastering', 'sid-code, mastering', 'sid code - mastering code', 'sid code (mastering code)', 'sid code: mastering code', 'sid mastering code', 'sid - mastering code', 'sid (mastering code)', 'sid mastetring code', 'cd sid master', 'cd sid mastering', 'cd sid mastering code', 'cd: sid mastering code', 'cd, sid mastering code', 'cd, sid - mastering code', 'cds, mastering sid code', 'mastered sid code', 'masterd sid code', 'masteirng sid code', 'sid master code', 'mastering sid codes', 'mastering sid', 'mastering sid-code', 'sid master', 's.i.d. master code', 'sid (master)', 'sid mastering', 'sid masterind code', 'sid (mastering)', 'cd1 mastering sid code', 'cd2 mastering sid code', 'mastering s.i.d. code', 'mastering sid code cd2', 'mastering sid code cd3', 'cd mastering sid code', 'the mastering sid code', 'mastering sid code cd1', 'mastering sid code dvd', 'sid code mastering cd1', 'sid mastering code cd 1', 'sid mastering code cd1', 'cd centre etching - sid mastering code', 'mastering sid сode', 'masterin sid code', 'masterring sid code', 'cd centre etching - mastering sid code', 'sid mastering code cd2', 'master s.i.d.', 'master s.i.d. code'])

mouldsids = set(['mould sid code', 'mould sid', 'mold sid', 'mold sid code', 'modul sid code', 'moould sid code', 'moudl sid code', 'moud sid code', 'moulded sid code', 'mouldering sid-code', 'moulding sid code', 'mouldg sid code', 'moulde sid code', 'mould sid-code', 'mould sid codes', 'moul sid code', 'muold sid code', 'sid code mold', 'sid code mould', 'sid-code (mould)', 'sid code: mould', 'sid code, mould', 'sid code - mould', 'sid code (moild)', 'sid code [mould]', '(sid code, mould)', 'sid-code, mould', 'sid code (mould)', 'sid code - mould code', 'sid code (mould code)', 'sid code: mould code', 'sid code moulded', 'sid code (moulded)', 'sid code, moulding', 'sid code mould (inner ring)', 'sid code (mould - inner ring)', 'sid code (mould, inner ring)', 'sid code mould - inner ring', 'sid (mold code)', 'sid mold code', 'sid moul code', 'sid mould', 'sid - mould', 'sid (mould)', 'sid, mould', 'sid - mould code', 'sid mould code', 'sid mould code cd1', 'sid mould code cd 1', 'sid mould code cd2', 'sid mould code cd 2', 'sid mould code disc 1', 'sid mould code, disc 1', 'sid mould code - disc 1', 'sid mould code disc 2', 'sid mould code, disc 2', 'sid mould code - disc 2', 'sid mould code disc 3', 'sid mould code - disc 3', 'sid mould code disc 4', 'sid mould code disc 5', 'sid mould disc 1', 'sid mould disc 2', 'sid mould disc 3', 'sid mould disc 4', 'sid mould disc 5', 'sid mould disc 6', 'sid muold code', 'sid mouls code', 'cd sid mould', 'cd sid mould code', 'cd, sid mould code', 'cd, sid - mould code', 'cds, mould sid code', 'mould sid code cd1', 'mould sid code cd2', 'sid-code mould', 'mould sid code, variant 1', 'mould sid code, variant 2', 'mould sid code dvd', 'mould sid code - dvd', 'mould sid code [dvd]', 'mould sid code, dvd', 'mould sid code (dvd)', 'mould sid code cd', 'mould sid-code', 'dvd mould sid code', 'dvd, mould sid code', 'dvd (mould sid code)', 'dvd - mould sid code', 'cd1 mould sid code', 'cd 1 mould sid code', 'cd1 : mould sid code', 'cd1, mould sid code', 'cd2 mould sid code', 'cd centre etching - mould sid code', 'cd centre etching - sid mould code', 'mould sid. code', 'mould sid code, both discs', 'cd mould (sid)', 'cd mould sid', 'cd mould sid code', 'cd - mould sid code', 'cd: mould sid code', 'cd mould, sid code', 'cd (mould sid code)', 'cd, mould sid code', 'disc 1 mould (sid)', 'disc 1 mould sid code', 'disc 1 (mould sid code)', '(disc 1) mould sid code', 'disc 1 - mould sid code', 'disc (1) - mould sid code', 'disc 1 sid code moulded', 'disc 1 sid mould', 'disc 1 sid mould code', 'disc 1 - sid mould code', 'disc 2 mould sid code', 'disc 2 (mould sid code)', '(disc 2) mould sid code', 'disc (2) - mould sid code', 'dvd sid mould code', 'dvd: sid mould code', 'dvd1 mould sid code', 'dvd1 sid code mould', 'dvd2 mould sid code', 'dvd2 sid code mould', 'mould sid code 1', 'mould sid code 2', 'mould sid code both discs', 'mould sid code (both discs)', 'mould sid code - cd1', 'mould sid code, cd', 'mould sid code cd 1', 'mould sid code (cd1)', 'mould sid code [cd]', 'mould sid code - cd1', 'mould sid code cd1 & cd2', 'mould sid code (cd 2)', 'mould sid code (cd2)', 'mould sid code - cd2', 'mould sid code disc 2', 'mould sid code dvd1', 'mould s.i.d.', 'mould s.i.d. code', 'moulds.i.d. code', 's.i.d. mould code', 's.i.d. moulding code', 'modul sid code (both discs)'])

## a list of creative commons identifiers
creativecommons = ['CC-BY-NC-ND', 'CC-BY-ND', 'CC-BY-SA', 'ShareAlike']

## a class with a handler for the SAX parser
class discogs_handler(xml.sax.ContentHandler):
	def __init__(self, config_settings):
		## many default settings
		self.incountry = False
		self.inrole = False
		self.inreleased = False
		self.inspars = False
		self.inother = False
		self.indeposito = False
		self.inlabelcode = False
		self.inbarcode = False
		self.inasin = False
		self.inisrc = False
		self.inmasteringsid = False
		self.inmouldsid = False
		self.inrightssociety = False
		self.intracklist = False
		self.invideos = False
		self.innotes = False
		self.release = None
		self.country = None
		self.role = None
		self.indescription = False
		self.indescriptions = False
		self.debugcount = 0
		self.count = 0
		self.prev = None
		self.formattexts = set([])
		self.iscd = False
		self.isrejected = False
		self.isdraft = False
		self.isdeleted = False
		self.depositofound = False
		self.config = config_settings
		self.contentbuffer = ''
		if 'check_credits' in self.config:
			creditsfile = open(self.config['creditsfile'], 'r')
			self.credits = set(map(lambda x: x.strip(), creditsfile.readlines()))
			creditsfile.close()

	## startElement() is called every time a new XML element is parsed
	def startElement(self, name, attrs):
		## first process the contentbuffer of the previous
		## element that was stored.
		if self.incountry:
			self.country = self.contentbuffer
		if self.config['check_spelling_cs']:
			if self.country == 'Czechoslovakia' or self.country == 'Czech Republic':
				## People use 0x115 instead of 0x11B, which look very similar but 0x115 is not valid
				## in the Czech alphabet. Check for all data except the YouTube playlist.
				## https://www.discogs.com/group/thread/757556
				if not self.invideos:
					if chr(0x115) in self.contentbuffer:
						self.count += 1
						print('%8d -- Czech character (0x115): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
		if self.inrole:
			if 'check_credits' in self.config:
				roledata = self.contentbuffer.strip()
				if roledata != '':
					if not '[' in roledata:
						roles = map(lambda x: x.strip(), roledata.split(','))
						for role in roles:
							if role == '':
								continue
							if not role in self.credits:
								self.count += 1
								print('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (self.count, role, str(self.release)))
								sys.stdout.flush()
					else:
						## sometimes there is an additional description in the role in between [ and ]
						rolesplit = roledata.split('[')
						for rs in rolesplit:
							if ']' in rs:
								rs_tmp = rs
								while ']' in rs_tmp:
									rs_tmp = rs_tmp.split(']', 1)[1]
								roles = map(lambda x: x.strip(), rs_tmp.split(','))
								for role in roles:
									if role == '':
										continue
									## ugly hack because sometimes the extra data between [ and ]
									## appears halfway the words in a role, sigh.
									if role == 'By':
										continue
									if not role in self.credits:
										self.count += 1
										print('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (self.count, role, str(self.release)))
										sys.stdout.flush()
										continue
		elif self.indescription:
			if self.indescriptions:
				if 'Styrene' in self.contentbuffer:
					pass
		elif self.inreleased:
			if self.config['check_month']:
				monthres = re.search('-(\d+)-', self.contentbuffer)
				if monthres != None:
					monthnr = int(monthres.groups()[0])
					if monthnr == 0:
						self.count += 1
						print('%8d -- Month 00: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
					elif monthnr > 12:
						self.count += 1
						print('%8d -- Month impossible (%d): https://www.discogs.com/release/%s' % (self.count, monthnr, str(self.release)))
					sys.stdout.flush()
			if self.contentbuffer != '':
				try:
					self.year = int(self.contentbuffer.split('-', 1)[0])
				except:
					if self.config['check_year']:
						self.count += 1
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
			if self.config['check_creative_commons']:
				ccfound = False
				for cc in creativecommons:
					if cc in self.contentbuffer:
						self.count += 1
						print('%8d -- Creative Commons reference (%s): https://www.discogs.com/release/%s' % (self.count, cc, str(self.release)))
						ccfound = True
						break

				if not ccfound:
					if 'creative commons' in self.contentbuffer.lower():
						self.count += 1
						print('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						ccfound = True
		if self.intracklist and self.inposition:
			if self.config['check_tracklisting']:
				if self.tracklistcorrect != False:
					if len(self.formattexts) == 1:
						for f in ['Vinyl', 'Cassette', 'Shellac', '8-Track Cartridge']:
							if f in self.formattexts:
								try:
									int(self.contentbuffer)
									self.count += 1
									print('%8d -- Tracklisting (%s): https://www.discogs.com/release/%s' % (self.count, f, str(self.release)))
									self.tracklistcorrect = False
								except:
									pass
		sys.stdout.flush()

		## now reset some values
		self.incountry = False
		self.inreleased = False
		self.inrole = False
		self.inspars = False
		self.inother = False
		self.inlabelcode = False
		self.inbarcode = False
		self.inasin = False
		self.inisrc = False
		self.inmasteringsid = False
		self.inmouldsid = False
		self.inrightssociety = False
		self.indeposito = False
		self.innotes = False
		self.indescription = False
		self.intitle = False
		self.inposition = False
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
			self.tracklistcorrect = True
			self.year = None
			self.role = None
			self.country = None
			self.intracklist = False
			self.invideos = False
			self.formattexts = set([])
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
		if self.isrejected or self.isdraft or self.isdeleted:
			return
		if name == 'descriptions':
			self.indescriptions = True
		elif not name == 'description':
			self.indescriptions = False

		if name == 'country':
			self.incountry = True
		elif name == 'role':
			self.inrole = True
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
		elif name == 'videos':
			self.invideos = True
			self.intracklist = False
		elif name == 'companies':
			self.invideos = False
		elif name == 'title':
			self.intitle = True
		elif name == 'position':
			self.inposition = True
		elif name == 'format':
			for (k,v) in attrs.items():
				if k == 'name':
					if v == 'CD':
						self.iscd = True
					self.formattexts.add(v)
				elif k == 'text':
					if v != '':
						if self.config['check_spars_code']:
							tmpspars = v.lower().strip()
							for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
								tmpspars = tmpspars.replace(s, '')
							if tmpspars in validsparscodes:
								self.count += 1
								self.prev = self.release
								print('%8d -- Possible SPARS Code (in Format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
						if self.config['check_label_code']:
							if v.lower().startswith('lc'):
								if labelcodere.match(v.lower()) != None:
									self.count += 1
									self.prev = self.release
									print('%8d -- Possible Label Code (in Format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									return
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
				elif v == 'Mastering SID Code':
					self.inmasteringsid = True
				elif v == 'Mould SID Code':
					self.inmouldsid = True
				elif v == 'Other':
					self.inother = True
			if 'value' in attritems:
				v = attritems['value']
				if not self.config['reportall']:
					if self.prev == self.release:
						return
				if self.config['check_creative_commons']:
					if 'creative commons' in v.lower():
						self.count += 1
						print('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
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
							tmpspars = v.lower().strip()
							for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
								tmpspars = tmpspars.replace(s, '')

							## just check a few other possibilities of possible SPARS codes
							if tmpspars in validsparscodes:
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
					if self.config['check_asin']:
						## temporary hack, move to own configuration option
						asinstrict = False
						if not asinstrict:
							tmpasin = v.strip().replace('-', '')
						else:
							tmpasin = v
						if not len(tmpasin.split(':')[-1].strip()) == 10:
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
				if self.inmouldsid:
					## temporary hack, move to own configuration option
					mould_sid_strict = False
					if self.config['check_mould_sid']:
						if v.strip() == 'none':
							return
						## cleanup first for not so heavy formatting booboos
						mould_tmp = v.strip().lower().replace(' ', '')
						mould_tmp = mould_tmp.replace('-', '')
						## some people insist on using ƒ instead of f
						mould_tmp = mould_tmp.replace('ƒ', 'f')
						res = mouldsidre.match(mould_tmp)
						if res == None:
							self.count += 1
							self.prev = self.release
							print('%8d -- Mould SID Code (value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if mould_sid_strict:
							mould_split = mould_tmp.split('ifpi', 1)[-1]
							for ch in ['i', 'o', 's', 'q']:
								if ch in mould_split[-2:]:
									self.count += 1
									self.prev = self.release
									print('%8d -- Mould SID Code (strict value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									return
						## rough check to find SID codes for formats other than CD/CD-like
						if len(self.formattexts) == 1:
							for fmt in set(['Vinyl', 'Cassette', 'Shellac', 'File', 'VHS', 'DCC', 'Memory Stick', 'Edison Disc']):
								if fmt in self.formattexts:
									self.count += 1
									self.prev = self.release
									print('%8d -- Mould SID Code (Wrong Format: %s): https://www.discogs.com/release/%s' % (self.count, fmt, str(self.release)))
									return
						if self.year != None:
							if self.year < 1993:
								self.count += 1
								self.prev = self.release
								print('%8d -- SID Code (wrong year): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
				if self.inmasteringsid:
					if self.config['check_mastering_sid']:
						if v.strip() == 'none':
							return
						## cleanup first for not so heavy formatting booboos
						master_tmp = v.strip().lower().replace(' ', '')
						master_tmp = master_tmp.replace('-', '')
						## some people insist on using ƒ instead of f
						master_tmp = master_tmp.replace('ƒ', 'f')
						res = masteringsidre.match(master_tmp)
						if res == None:
							self.count += 1
							self.prev = self.release
							print('%8d -- Mastering SID Code (value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						## rough check to find SID codes for formats other than CD/CD-like
						if len(self.formattexts) == 1:
							for fmt in set(['Vinyl', 'Cassette', 'Shellac', 'File', 'VHS', 'DCC', 'Memory Stick', 'Edison Disc']):
								if fmt in self.formattexts:
									self.count += 1
									self.prev = self.release
									print('%8d -- Mastering SID Code (Wrong Format: %s): https://www.discogs.com/release/%s' % (self.count, fmt, str(self.release)))
									return
						if self.year != None:
							if self.year < 1993:
								self.count += 1
								self.prev = self.release
								print('%8d -- SID Code (wrong year): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
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
											## correct the year. This won't work correctly after 2099.
											if depositoyear <= currentyear - 2000:
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
									elif depositoyear > currentyear:
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
				if self.country == 'India':
					if self.config['check_pkd']:
						if 'pkd' in v.lower() or "production date" in v.lower():
							if self.year != None:
								## try a few variants
								pkdres = re.search("\d{1,2}/((?:19|20)?\d{2})", v)
								if pkdres != None:
									pkdyear = int(pkdres.groups()[0])
									if pkdyear < 100:
										## correct the year. This won't work correctly after 2099.
										if pkdyear <= currentyear - 2000:
											pkdyear += 2000
										else:
											pkdyear += 1900
									if pkdyear < 1900:
										self.count += 1
										self.prev = self.release
										print("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif pkdyear > currentyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif self.year < pkdyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Indian PKD (release date earlier): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
							else:
								self.count += 1
								self.prev = self.release
								print('%8d -- India PKD code (no year): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
			if 'description' in attritems:
				v = attritems['description']
				attrvalue = attritems['value']
				if not self.config['reportall']:
					if self.prev == self.release:
						return
				self.description = v.lower()
				if self.config['check_spelling_cs']:
					## People use 0x115 instead of 0x11B, which look very similar but 0x115 is not valid
					## in the Czech alphabet.
					## https://www.discogs.com/group/thread/757556
					if self.country == 'Czechoslovakia' or self.country == 'Czech Republic':
						if chr(0x115) in attrvalue or chr(0x115) in self.description:
							self.count += 1
							print('%8d -- Czech character (0x115): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
				if self.config['check_creative_commons']:
					if 'creative commons' in self.description:
						self.count += 1
						print('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
				## squash repeated spaces
				self.description = re.sub('\s+', ' ', self.description)
				if self.config['check_rights_society']:
					if not self.inrightssociety:
						if self.description in rights_societies_ftf:
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
								return
				if self.config['check_asin']:
					if not self.inasin and self.description.startswith('asin'):
						self.count += 1
						self.prev = self.release
						print('%8d -- ASIN (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.config['check_isrc']:
					if not self.inisrc:
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
					if not self.inmasteringsid:
						if self.description.strip() in ['source identification code', 'sid', 'sid code', 'sid-code']:
							self.count += 1
							self.prev = self.release
							print('%8d -- Unspecified SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if self.description.strip() in masteringsids:
							self.count += 1
							self.prev = self.release
							print('%8d -- Mastering SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if self.description.strip() in ['sid code matrix', 'sid code - matrix', 'sid code (matrix)', 'sid-code, matrix', 'sid-code matrix', 'sid code (matrix ring)', 'sid code, matrix ring', 'sid code: matrix ring']:
							self.count += 1
							self.prev = self.release
							print('%8d -- Possible Mastering SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				if self.config['check_mould_sid']:
					if not self.inmouldsid:
						if self.description.strip() in ['source identification code', 'sid', 'sid code', 'sid-code']:
							self.count += 1
							self.prev = self.release
							print('%8d -- Unspecified SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if self.description.strip() in mouldsids:
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
					else:
						if self.config['check_deposito']:
							if self.indeposito:
								return
				elif self.country == 'India':
					if self.config['check_pkd']:
						if 'pkd' in self.description or "production date" in self.description:
							if self.year != None:
								## try a few variants
								pkdres = re.search("\d{1,2}/((?:19|20)?\d{2})", attrvalue)
								if pkdres != None:
									pkdyear = int(pkdres.groups()[0])
									if pkdyear < 100:
										## correct the year. This won't work correctly after 2099.
										if pkdyear <= currentyear - 2000:
											pkdyear += 2000
										else:
											pkdyear += 1900
									if pkdyear < 1900:
										self.count += 1
										self.prev = self.release
										print("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif pkdyear > currentyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif self.year < pkdyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Indian PKD (release date earlier): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
							else:
								self.count += 1
								self.prev = self.release
								print('%8d -- India PKD code (no year): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
				elif self.country == 'Czechoslovakia':
					if self.config['check_manufacturing_date_cs']:
						## config hack, needs to be in its own configuration option
						strict_cs = False
						if 'date' in self.description:
							if self.year != None:
								manufacturing_date_res = re.search("(\d{2})\s+\d$", attrvalue.rstrip())
								if manufacturing_date_res != None:
									manufacturing_year = int(manufacturing_date_res.groups()[0])
									if manufacturing_year < 100:
										manufacturing_year += 1900
										if manufacturing_year > self.year:
											self.count += 1
											self.prev = self.release
											print("%8d -- Czechoslovak manufacturing date (release year wrong): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
										## possibly this check makes sense, but not always
										elif manufacturing_year < self.year and strict_cs:
											self.count += 1
											self.prev = self.release
											print("%8d -- Czechoslovak manufacturing date (release year possibly wrong): https://www.discogs.com/release/%s" % (self.count, str(self.release)))

				## debug code to print descriptions that were skipped.
				## Useful to find misspellings of various fields
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

	## first some sanity checks for the gzip compressed releases file
	if args.datadump == None:
		parser.error("Data dump file missing")

	if not os.path.exists(args.datadump):
		parser.error("Data dump file does not exist")

	if not os.path.isfile(args.datadump):
		parser.error("Data dump file is not a file")

	## then some checks for the configuration file
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

	## process the configuration file and store settings
	config_settings = {}

	for section in config.sections():
		if section == 'cleanup':
			## store settings for depósito legal checks
			try:
				if config.get(section, 'deposito') == 'yes':
					config_settings['check_deposito'] = True
				else:
					config_settings['check_deposito'] = False
			except Exception:
				config_settings['check_deposito'] = True

			## store settings for rights society checks
			try:
				if config.get(section, 'rights_society') == 'yes':
					config_settings['check_rights_society'] = True
				else:
					config_settings['check_rights_society'] = False
			except Exception:
				config_settings['check_rights_society'] = True

			## store settings for rights society checks
			try:
				if config.get(section, 'label_code') == 'yes':
					config_settings['check_label_code'] = True
				else:
					config_settings['check_label_code'] = False
			except Exception:
				config_settings['check_label_code'] = True

			## store settings for ISRC checks
			try:
				if config.get(section, 'isrc') == 'yes':
					config_settings['check_isrc'] = True
				else:
					config_settings['check_isrc'] = False
			except Exception:
				config_settings['check_isrc'] = True

			## store settings for ASIN checks
			try:
				if config.get(section, 'asin') == 'yes':
					config_settings['check_asin'] = True
				else:
					config_settings['check_asin'] = False
			except Exception:
				config_settings['check_asin'] = True

			## store settings for mastering SID checks
			try:
				if config.get(section, 'mastering_sid') == 'yes':
					config_settings['check_mastering_sid'] = True
				else:
					config_settings['check_mastering_sid'] = False
			except Exception:
				config_settings['check_mastering_sid'] = True

			## store settings for mould SID checks
			try:
				if config.get(section, 'mould_sid') == 'yes':
					config_settings['check_mould_sid'] = True
				else:
					config_settings['check_mould_sid'] = False
			except Exception:
				config_settings['check_mould_sid'] = True

			## store settings for SPARS Code checks
			try:
				if config.get(section, 'spars') == 'yes':
					config_settings['check_spars_code'] = True
				else:
					config_settings['check_spars_code'] = False
			except Exception:
				config_settings['check_spars_code'] = True

			## store settings for Indian PKD checks
			try:
				if config.get(section, 'pkd') == 'yes':
					config_settings['check_pkd'] = True
				else:
					config_settings['check_pkd'] = False
			except Exception:
				config_settings['check_pkd'] = True

			## check for Czechoslovak manufacturing dates
			try:
				if config.get(section, 'manufacturing_date_cs') == 'yes':
					config_settings['check_manufacturing_date_cs'] = True
				else:
					config_settings['check_manufacturing_date_cs'] = False
			except Exception:
				config_settings['check_manufacturing_date_cs'] = True

			## check for Czechoslovak and Czech spelling (0x115 used instead of 0x11B)
			try:
				if config.get(section, 'spelling_cs') == 'yes':
					config_settings['check_spelling_cs'] = True
				else:
					config_settings['check_spelling_cs'] = False
			except Exception:
				config_settings['check_spelling_cs'] = True

			## store settings for tracklisting checks, default True
			try:
				if config.get(section, 'tracklisting') == 'yes':
					config_settings['check_tracklisting'] = True
				else:
					config_settings['check_tracklisting'] = False
			except Exception:
				config_settings['check_tracklisting'] = True

			## store settings for credits list checks
			try:
				if config.get(section, 'credits') == 'yes':
					creditsfile = config.get(section, 'creditsfile')
					if os.path.exists(creditsfile):
						config_settings['creditsfile'] = creditsfile
						config_settings['check_credits'] = True
				else:
					config_settings['check_credits'] = False
			except Exception:
				config_settings['check_credits'] = False

			## store settings for URLs in Notes checks
			try:
				if config.get(section, 'html') == 'yes':
					config_settings['check_html'] = True
				else:
					config_settings['check_html'] = False
			except Exception:
				config_settings['check_html'] = True


			## month is 00 check: default is False
			try:
				if config.get(section, 'month') == 'yes':
					config_settings['check_month'] = True
				else:
					config_settings['check_month'] = False
			except Exception:
				config_settings['check_month'] = False

			## year is wrong check: default is False
			try:
				if config.get(section, 'year') == 'yes':
					config_settings['check_year'] = True
				else:
					config_settings['check_year'] = False
			except Exception:
				config_settings['check_year'] = False

			## reporting all: default is False
			try:
				if config.get(section, 'reportall') == 'yes':
					config_settings['reportall'] = True
				else:
					config_settings['reportall'] = False
			except Exception:
				config_settings['reportall'] = False

			## debug: default is False
			try:
				if config.get(section, 'debug') == 'yes':
					config_settings['debug'] = True
				else:
					config_settings['debug'] = False
			except Exception:
				config_settings['debug'] = False

			## report creative commons references: default is False
			try:
				if config.get(section, 'creative_commons') == 'yes':
					config_settings['check_creative_commons'] = True
				else:
					config_settings['check_creative_commons'] = False
			except Exception:
				config_settings['check_creative_commons'] = False

	configfile.close()

	## create a SAX parser and feed the gzip compressed file to it
	dumpfileparser = xml.sax.make_parser()
	dumpfileparser.setContentHandler(discogs_handler(config_settings))
	try:
		dumpfile = gzip.open(args.datadump, "rb")
	except Exception:
		print("Cannot open dump file", file=sys.stderr)
		sys.exit(1)
	dumpfileparser.parse(dumpfile)

	dumpfile.close()

if __name__ == "__main__":
	main(sys.argv)
