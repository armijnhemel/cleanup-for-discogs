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
## The results that are printed by this script are by no means complete or accurate
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0-only
##
## Copyright 2017-2018 - Armijn Hemel

import xml.sax
import sys, os, gzip, re, datetime
import argparse, configparser
import discogssmells

## grab the current year. Make sure to set the clock of your machine
## to the correct date or use NTP!
currentyear = datetime.datetime.utcnow().year

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
		self.inmatrix = False
		self.inrightssociety = False
		self.intracklist = False
		self.invideos = False
		self.innotes = False
		self.incompany = False
		self.incompanyid = False
		self.inartistid = False
		self.noartist = False
		self.release = None
		self.country = None
		self.role = None
		self.indescription = False
		self.indescriptions = False
		self.ingenre = False
		self.inartist = False
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
		if self.config['check_credits']:
			creditsfile = open(self.config['creditsfile'], 'r')
			self.credits = set(map(lambda x: x.strip(), creditsfile.readlines()))
			creditsfile.close()

	## startElement() is called every time a new XML element is parsed
	def startElement(self, name, attrs):
		## first process the contentbuffer of the previous
		## element that was stored.
		if self.ingenre:
			self.genres.add(self.contentbuffer)
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
			if self.noartist:
				wrongrolefornoartist = True
				for r in ['Other', 'Artwork By', 'Executive Producer', 'Photography', 'Written By']:
					if r in self.contentbuffer.strip():
						wrongrolefornoartist = False
						break
				if wrongrolefornoartist:
					pass
					#print(self.contentbuffer.strip(), " -- https://www.discogs.com/release/%s" % str(self.release))
			if self.config['check_credits']:
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
		elif self.inartistid:
			if self.contentbuffer == '0':
				self.count += 1
				print('%8d -- Artist not in database: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
				sys.stdout.flush()
				self.noartist = True
			else:
				self.noartist = False
			## TODO: check for genres, as No Artist is often confused with Unknown Artist
			#if self.contentbuffer == '118760':
			#	if len(self.genres) != 0:
			#		print("https://www.discogs.com/artist/%s" % self.contentbuffer, "https://www.discogs.com/release/%s" % str(self.release))
			#		print(self.genres)
			#		sys.exit(0)
			self.artists.add(self.contentbuffer)
		elif self.incompanyid:
			if self.config['check_labels']:
				if self.year != None:
					## check for:
					## https://www.discogs.com/label/205-Fontana
					## https://www.discogs.com/label/7704-Philips
					if self.contentbuffer == '205':
						if self.year < 1957:
							self.count += 1
							print('%8d -- Label (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '7704':
						if self.year < 1950:
							self.count += 1
							print('%8d -- Label (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
			if self.config['check_plants']:
				if self.year != None:
					## check for:
					## https://www.discogs.com/label/358102-PDO-USA
					## https://www.discogs.com/label/360848-PMDC-USA
					## https://www.discogs.com/label/266782-UML
					## https://www.discogs.com/label/381697-EDC-USA
					if self.contentbuffer == '358102':
						if self.year < 1986:
							self.count += 1
							print('%8d -- Pressing plant PDO, USA (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '360848':
						if self.year < 1992:
							self.count += 1
							print('%8d -- Pressing plant PMDC, USA (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '266782':
						if self.year < 1999:
							self.count += 1
							print('%8d -- Pressing plant UML (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '381697':
						if self.year < 2005:
							self.count += 1
							print('%8d -- Pressing plant EDC, USA (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))

					## check for
					## https://www.discogs.com/label/358025-PDO-Germany
					## https://www.discogs.com/label/342158-PMDC-Germany
					## https://www.discogs.com/label/331548-Universal-M-L-Germany
					## https://www.discogs.com/label/384133-EDC-Germany
					if self.contentbuffer == '358025':
						if self.year < 1986:
							self.count += 1
							print('%8d -- Pressing plant PDO, Germany (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '342158':
						if self.year < 1993:
							self.count += 1
							print('%8d -- Pressing plant PMDC, Germany (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '331548':
						if self.year < 1999:
							self.count += 1
							print('%8d -- Pressing plant Universal, M & L, Germany (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					elif self.contentbuffer == '384133':
						if self.year < 2005:
							self.count += 1
							print('%8d -- Pressing plant EDC, Germany (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))

					## https://www.discogs.com/label/265455-PMDC
					if self.contentbuffer == '265455':
						if self.year < 1992:
							self.count += 1
							print('%8d -- Pressing plant PMDC, France (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))

					'''
					## https://www.discogs.com/label/34825-Sony-DADC
					if self.contentbuffer == '34825':
						if self.year < 2000:
							self.count += 1
							print('%8d -- Pressing plant Sony DADC (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
					'''

					## check for:
					##
					## Dureco:
					## -------
					## https://www.discogs.com/label/7207-Dureco
					## https://dureco.wordpress.com/2014/12/09/opening-cd-fabriek-weesp/
					## https://www.anderetijden.nl/aflevering/141/De-komst-van-het-schijfje (starting 22:25)
					## https://books.google.nl/books?id=yyQEAAAAMBAJ&pg=RA1-PA37&lpg=RA1-PA37&dq=dureco+CDs+1987&source=bl&ots=cwc3WPM3Nw&sig=t0man_qWguylE9HEyqO39axo8kM&hl=nl&sa=X&ved=0ahUKEwjdme-xxcTZAhXN26QKHURgCJc4ChDoAQg4MAE#v=onepage&q&f=false
					## https://www.youtube.com/watch?v=laDLvlj8tIQ
					## https://krantenbankzeeland.nl/issue/pzc/1987-09-19/edition/0/page/21
					##
					## Since Dureco was also a distributor there are sometimes false positives
					##
					## Microservice:
					## -------------
					## https://www.discogs.com/label/300888-Microservice-Microfilmagens-e-Reprodu%C3%A7%C3%B5es-T%C3%A9cnicas-Ltda
					##
					## MPO:
					## ----
					## https://www.discogs.com/label/56025-MPO
					##
					## Nimbus:
					## ------
					## https://www.discogs.com/label/93218-Nimbus
					##
					## Mayking:
					## -------
					## https://www.discogs.com/label/147881-Mayking
					##
					## EMI Uden:
					## --------
					## https://www.discogs.com/label/266256-EMI-Uden
					##
					## WEA Mfg Olyphant:
					## -----------------
					## https://www.discogs.com/label/291934-WEA-Mfg-Olyphant
					##
					## Opti.Me.S:
					## ----------
					## https://www.discogs.com/label/271323-OptiMeS
					##
					## Format: (plant id, year production started, label name)
					plants = [('7207', 1987, 'Dureco'), ('300888', 1987, 'Microservice'), ('56025', 1984, 'MPO'), ('93218', 1984, 'Nimbus'), ('147881', 1985, 'Mayking'), ('266256', 1989, 'EMI Uden'), ('291934', 1996, 'WEA Mfg Olyphant'), ('271323', 1986, 'Opti.Me.S')]
					for pl in plants:
						if self.contentbuffer == pl[0]:
							if 'CD' in self.formattexts:
								if self.year < pl[1]:
									self.count += 1
									print('%8d -- Pressing plant %s (possibly wrong year %s): https://www.discogs.com/release/%s' % (self.count, pl[2], self.year, str(self.release)))
									break

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
					for d in discogssmells.depositores:
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
				for cc in discogssmells.creativecommons:
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
			'''
			## https://en.wikipedia.org/wiki/Phonograph_record#Microgroove_and_vinyl_era
			if 'Vinyl' in self.formattexts:
				if self.year != None:
					if self.year < 1948:
						self.count += 1
						print('%8d -- Impossible year (%d): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
			'''
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
									return
								except:
									pass
						if self.formatmaxqty == 1:
							if self.contentbuffer.strip() != '' and self.contentbuffer.strip() != '-' and self.contentbuffer in self.tracklistpositions:
								self.count += 1
								print('%8d -- Tracklisting reuse (%s, %s): https://www.discogs.com/release/%s' % (self.count, list(self.formattexts)[0], self.contentbuffer, str(self.release)))
								return
							self.tracklistpositions.add(self.contentbuffer)
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
		self.inmatrix = False
		self.inrightssociety = False
		self.indeposito = False
		self.innotes = False
		self.indescription = False
		self.intitle = False
		self.ingenre = False
		self.inposition = False
		self.contentbuffer = ''
		if not self.incompany:
			self.incompanyid = False
		self.inartistid = False
		if name == "release":
			## new release entry, so reset many fields
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
			self.incompany = False
			self.incompanyid = False
			self.inartistid = False
			self.noartist = False
			self.ingenre = False
			self.formattexts = set([])
			self.artists = set([])
			self.formatmaxqty = 0
			self.genres = set([])
			self.tracklistpositions = set()
			self.isrcpositions = set()
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

		if name == 'artist':
			self.inartist = True
			self.incompany = False
			self.noartist = False
		if name == 'company':
			self.incompany = True
			self.inartist = False
		if name == 'id':
			if self.incompany:
				self.incompanyid = True
			if self.inartist:
				self.inartistid = True
				self.noartist = False
		if name == 'country':
			self.incountry = True
		elif name == 'role':
			self.inrole = True
		elif name == 'label':
			for (k,v) in attrs.items():
				if k == 'name':
					if self.config['check_label_name']:
						if v == 'London':
							self.count += 1
							self.prev = self.release
							print('%8d -- Wrong label (London): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				elif k == 'catno':
					catno = v.lower()
					if self.config['check_label_code']:
						if catno.startswith('lc'):
							if discogssmells.labelcodere.match(catno) != None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Possible Label Code (in Catalogue Number): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					if self.config['check_deposito']:
						## now check for D.L.
						dlfound = False
						for d in discogssmells.depositores:
							result = d.search(catno)
							if result != None:
								for depositovalre in discogssmells.depositovalres:
									if depositovalre.search(catno) != None:
										dlfound = True
										break

						if dlfound:
							self.count += 1
							self.prev = self.release
							print('%8d -- Possible Depósito Legal (in Catalogue Number): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
		elif name == 'genre':
			self.ingenre = True
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
			curformat = None
			for (k,v) in attrs.items():
				if k == 'name':
					if v == 'CD':
						self.iscd = True
					self.formattexts.add(v)
					curformat = v
				elif k == 'qty':
					if self.formatmaxqty == 0:
						self.formatmaxqty = max(self.formatmaxqty, int(v))
					else:
						self.formatmaxqty += int(v)
				elif k == 'text':
					if v != '':
						if self.config['check_spars_code']:
							tmpspars = v.lower().strip()
							for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
								tmpspars = tmpspars.replace(s, '')
							if tmpspars in discogssmells.validsparscodes:
								self.count += 1
								self.prev = self.release
								print('%8d -- Possible SPARS Code (in Format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
						if self.config['check_label_code']:
							if v.lower().startswith('lc'):
								if discogssmells.labelcodere.match(v.lower()) != None:
									self.count += 1
									self.prev = self.release
									print('%8d -- Possible Label Code (in Format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									return
						if self.config['check_cdg']:
							if v.lower().strip() == 'cd+g':
								self.count += 1
								self.prev = self.release
								print('%8d -- CD+G (in Format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
						if v == 'DMM':
							if curformat != 'Vinyl':
								print('%8d -- DMM (%s, in Format): https://www.discogs.com/release/%s' % (self.count, curformat, str(self.release)))

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
				elif v == 'Matrix / Runout':
					self.inmatrix = True
				elif v == 'Other':
					self.inother = True
			if 'value' in attritems:
				v = attritems['value']
				if not self.config['reportall']:
					if self.prev == self.release:
						return
				if 'MADE IN USA BY PDMC' in v:
					self.count += 1
					self.prev = self.release
					print("%8d -- Matrix (PDMC instead of PMDC): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
				elif 'MADE IN GERMANY BY PDMC' in v:
					self.count += 1
					self.prev = self.release
					print("%8d -- Matrix (PDMC instead of PMDC): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
				elif 'MADE IN FRANCE BY PDMC' in v:
					self.count += 1
					self.prev = self.release
					print("%8d -- Matrix (PDMC instead of PMDC): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
				elif 'PDMC FRANCE' in v:
					self.count += 1
					self.prev = self.release
					print("%8d -- Matrix (PDMC instead of PMDC): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
				if self.config['check_creative_commons']:
					if 'creative commons' in v.lower():
						self.count += 1
						print('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
				if self.config['check_matrix']:
					if self.inmatrix:
						if self.year != None:
							if 'MFG BY CINRAM' in v and '#' in v and not 'USA' in v:
								cinramres = re.search('#(\d{2})',v)
								if cinramres != None:
									cinramyear = int(cinramres.groups()[0])
									## correct the year. This won't work correctly after 2099.
									if cinramyear <= currentyear - 2000:
										cinramyear += 2000
									else:
										cinramyear += 1900
									if cinramyear > currentyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Matrix (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif self.year < cinramyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Matrix (release date %d earlier than matrix year %d): https://www.discogs.com/release/%s" % (self.count, self.year, cinramyear, str(self.release)))
							elif 'P+O' in v:
								## https://www.discogs.com/label/277449-PO-Pallas
								pallasres = re.search('P\+O[–-]\d{4,5}[–-][ABCD]\d?\s+\d{2}[–-](\d{2})', v)
								if pallasres != None:
									pallasyear = int(pallasres.groups()[0])
									## correct the year. This won't work correctly after 2099.
									if pallasyear <= currentyear - 2000:
										pallasyear += 2000
									else:
										pallasyear += 1900
									if pallasyear > currentyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Matrix (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									elif self.year < pallasyear:
										self.count += 1
										self.prev = self.release
										print("%8d -- Matrix (release date %d earlier than matrix year %d): https://www.discogs.com/release/%s" % (self.count, self.year, pallasyear, str(self.release)))

				if self.inspars:
					if self.config['check_spars_code']:
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
						sparstocheck = []
						tmpspars = v.lower().strip()
						for s in ['.', ' ', '•', '·', '∙', '᛫', '[', ']', '-', '|', '/']:
							tmpspars = tmpspars.replace(s, '')
						if len(tmpspars) != 3:
							sparssplit = False
							for s in ['|', '/', ',', ' ', '&', '-', '+', '•']:
								if s in v.lower().strip():
									splitspars = list(map(lambda x: x.strip(), v.lower().strip().split(s)))
									if len(list(filter(lambda x: len(x) == 3, splitspars))) != len(splitspars):
										continue
									sparssplit = True
									break
							if not sparssplit:
								sparstocheck.append(tmpspars)
						else:
							sparstocheck.append(tmpspars)
						for sparscheck in sparstocheck:
							if not sparscheck in discogssmells.validsparscodes:
								wrongspars = True
							for s in sparscheck:
								if ord(s) > 256:
									self.count += 1
									self.prev = self.release
									print('%8d -- SPARS Code (wrong character set, %s): https://www.discogs.com/release/%s' % (self.count, v, str(self.release)))

							if wrongspars:
								self.count += 1
								self.prev = self.release
								print('%8d -- SPARS Code (format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
						if self.year != None:
							if self.year < 1984:
								self.count += 1
								self.prev = self.release
								print('%8d -- SPARS Code (impossible year): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
				elif not self.inother:
					if self.config['check_spars_code']:
						if v.lower() in discogssmells.validsparscodes:
							self.count += 1
							self.prev = self.release
							print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if 'd' in v.lower():
							tmpspars = v.lower().strip()
							for s in ['.', ' ', '•', '∙', '·', '᛫', '[', ']', '-', '|', '/', '︱']:
								tmpspars = tmpspars.replace(s, '')

							## just check a few other possibilities of possible SPARS codes
							if tmpspars in discogssmells.validsparscodes:
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
						if discogssmells.labelcodere.match(v.lower()) == None:
							self.count += 1
							self.prev = self.release
							print('%8d -- Label Code (value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				if self.inrightssociety:
					if self.config['check_label_code']:
						if v.lower().startswith('lc'):
							if discogssmells.labelcodere.match(v.lower()) != None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Label Code (in Rights Society): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					if self.config['check_rights_society']:
						for r in discogssmells.rights_societies_wrong:
							if r in v.upper():
								self.count += 1
								self.prev = self.release
								print('%8d -- Rights Society (possible wrong value): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								break
					if v.upper() in discogssmells.rights_societies_wrong_char:
						self.count += 1
						self.prev = self.release
						print('%8d -- Rights Society (wrong character set, %s): https://www.discogs.com/release/%s' % (self.count, v, str(self.release)))
				elif not self.inother:
					if self.config['check_rights_society']:
						if '/' in v:
							vsplits = v.split('/')
							for vsplit in vsplits:
								for r in discogssmells.rights_societies:
									if vsplit.upper().replace('.', '') == r or vsplit.upper().replace(' ', '') == r:
										self.count += 1
										self.prev = self.release
										print('%8d -- Rights Society: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
										break
						else:
							for r in discogssmells.rights_societies:
								if v.upper().replace('.', '') == r or v.upper().replace(' ', '') == r:
									self.count += 1
									self.prev = self.release
									print('%8d -- Rights Society: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									break
				if self.inbarcode:
					if self.config['check_label_code']:
						if v.lower().startswith('lc'):
							if discogssmells.labelcodere.match(v.lower()) != None:
								self.count += 1
								self.prev = self.release
								print('%8d -- Label Code (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					if self.country == 'Spain':
						if self.config['check_deposito'] and not self.depositofound:
							for depositovalre in discogssmells.depositovalres:
								if depositovalre.match(v.lower()) != None:
									self.count += 1
									self.prev = self.release
									print('%8d -- Depósito Legal (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
									return
					if self.config['check_rights_society']:
						for r in discogssmells.rights_societies:
							if v.upper().replace('.', '') == r or v.upper().replace(' ', '') == r:
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
					if self.config['check_rights_society']:
						for r in discogssmells.rights_societies:
							if v.upper().replace('.', '') == r or v.upper().replace(' ', '') == r:
								self.count += 1
								self.prev = self.release
								print('%8d -- Rights Society (in ISRC): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								break
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
						else:
							isrcres = re.match("\w{5}(\d{2})\d{5}", isrc_tmp)
							if isrcres == None:
								self.count += 1
								self.prev = self.release
								print('%8d -- ISRC (wrong format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								sys.stdout.flush()
								return
							if self.year != None:
								isrcyear = int(isrcres.groups()[0])
								if isrcyear < 100:
									## correct the year. This won't work correctly after 2099.
									if isrcyear <= currentyear - 2000:
										isrcyear += 2000
									else:
										isrcyear += 1900
								if isrcyear > currentyear:
									self.count += 1
									self.prev = self.release
									print("%8d -- ISRC (impossible year): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
								elif self.year < isrcyear:
									self.count += 1
									self.prev = self.release
									print("%8d -- ISRC (date earlier): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
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
						res = discogssmells.mouldsidre.match(mould_tmp)
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
						res = discogssmells.masteringsidre.match(master_tmp)
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
						if self.description in discogssmells.rights_societies_ftf:
							self.count += 1
							self.prev = self.release
							print('%8d -- Rights Society: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							for rs in discogssmells.rights_societies_wrong_char:
								if rs in attrvalue:
									self.count += 1
									self.prev = self.release
									print('%8d -- Rights Society (wrong character set, %s): https://www.discogs.com/release/%s' % (self.count, attrvalue, str(self.release)))
							return
				if self.config['check_label_code'] and not self.inlabelcode:
					if self.description in discogssmells.label_code_ftf:
						self.count += 1
						self.prev = self.release
						print('%8d -- Label Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
						return
				if self.config['check_spars_code']:
					if not self.inspars:
						sparsfound = False
						for spars in discogssmells.spars_ftf:
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
						for isrc in discogssmells.isrc_ftf:
							if isrc in self.description:
								self.count += 1
								self.prev = self.release
								print('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
								return
					else:
						if self.description.strip() in self.isrcpositions:
							self.count += 1
							self.prev = self.release
							print('%8d -- ISRC Code (description reuse %s): https://www.discogs.com/release/%s' % (self.count, self.description.strip(),str(self.release)))
						self.isrcpositions.add(self.description.strip())
				if self.config['check_mastering_sid']:
					if not self.inmasteringsid:
						if self.description.strip() in ['source identification code', 'sid', 'sid code', 'sid-code']:
							self.count += 1
							self.prev = self.release
							print('%8d -- Unspecified SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
						if self.description.strip() in discogssmells.masteringsids:
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
						if self.description.strip() in discogssmells.mouldsids:
							self.count += 1
							self.prev = self.release
							print('%8d -- Mould SID Code: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
							return
				if self.country == 'Spain':
					if self.config['check_deposito'] and not self.indeposito:
						found = False
						for d in discogssmells.depositores:
							result = d.search(self.description)
							if result != None:
								found = True
								break

						## sometimes the depósito value itself can be found in the free text field
						if not found:
							for depositovalre in discogssmells.depositovalres:
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

				elif self.country == 'Greece':
					if self.config['check_greek_license_number']:
						if "license" in self.description.strip() and self.year != None:
							licenseyearfound = False
							for sep in ['/', ' ', '-', ')', '\'', '.']:
								if licenseyearfound:
									break
								try:
									license_year = int(attrvalue.strip().rsplit(sep, 1)[1])
									if license_year < 100:
										license_year += 1900
									if license_year > self.year:
										self.count += 1
										self.prev = self.release
										print("%8d -- Greek license year wrong: https://www.discogs.com/release/%s" % (self.count, str(self.release)))
									licenseyearfound = True
								except:
									pass
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

			## store settings for label code checks
			try:
				if config.get(section, 'label_code') == 'yes':
					config_settings['check_label_code'] = True
				else:
					config_settings['check_label_code'] = False
			except Exception:
				config_settings['check_label_code'] = True

			## store settings for label name checks
			try:
				if config.get(section, 'label_name') == 'yes':
					config_settings['check_label_name'] = True
				else:
					config_settings['check_label_name'] = False
			except Exception:
				config_settings['check_label_name'] = True

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

			## store settings for Greek license number checks
			try:
				if config.get(section, 'greek_license_number') == 'yes':
					config_settings['check_greek_license_number'] = True
				else:
					config_settings['check_greek_license_number'] = False
			except Exception:
				config_settings['check_greek_license_number'] = True

			## store settings for CD+G checks
			try:
				if config.get(section, 'cdg') == 'yes':
					config_settings['check_cdg'] = True
				else:
					config_settings['check_cdg'] = False
			except Exception:
				config_settings['check_cdg'] = True

			## store settings for Matrix checks
			try:
				if config.get(section, 'matrix') == 'yes':
					config_settings['check_matrix'] = True
				else:
					config_settings['check_matrix'] = False
			except Exception:
				config_settings['check_matrix'] = True

			## store settings for label checks
			try:
				if config.get(section, 'labels') == 'yes':
					config_settings['check_labels'] = True
				else:
					config_settings['check_labels'] = False
			except Exception:
				config_settings['check_labels'] = True

			## store settings for manufacturing plant checks
			try:
				if config.get(section, 'plants') == 'yes':
					config_settings['check_plants'] = True
				else:
					config_settings['check_plants'] = False
			except Exception:
				config_settings['check_plants'] = True

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
			config_settings['check_credits'] = False
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
