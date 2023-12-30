#!/usr/bin/env python3

# Tool to discover 'smells' in the Discogs data dump. It prints a list of URLs
# of releases that need to be fixed.
#
# Why this happens:
#
# https://www.well.com/~doctorow/metacrap.htm
#
# Currently the following smells can be discovered:
#
# * depósito legal :: until recently the "depósito legal" data (for Spanish
#   releases) was essentially free text in the "Barcode and Other Identifiers"
#   section.
#   Since the August 2017 dump there is a separate field for it (and it has
#   effectively become a first class citizen in BaOI), but there are still many
#   releases where this information has not been changed and is in an "Other"
#   field in BaOI.
#   Also, there are many misspellings, making it more difficult to find.
# * label code :: until recently "Other" was used to specify the
#   label code, but since then there is a dedicated field called
#   "Label Code". There are still many entries that haven't been changed
#   though.
# * SPARS code :: in the past "Other" was used to specify the SPARS code, but
#   at some point a dedicated field called "SPARS Code" was introduced.
#   There are still many entries that haven't been changed though.
# * rights society :: until a few years ago "Other" was used to specify
#   the rights society, but since then there is a dedicated field called
#   "Rights Society". There are still many entries that haven't been changed
#   though.
# * month as 00 :: in older releases it was allowed to have the month as 00
#   but this is no longer allowed. When editing an entry that has 00 as the
#   month Discogs will throw an error.
# * hyperlinks :: in older releases it was OK to have normal HTML hyperlinks
#   but these have been replaced by markup:
#   https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-
#   There are still many releases where old hyperlinks are used.
#
# The results that are printed by this script are
# by no means complete or accurate
#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright 2017-2023 - Armijn Hemel

import configparser
import datetime
import gzip
import os
import pathlib
import re
import sys

from dataclasses import dataclass

import defusedxml.ElementTree as et

import click
import discogssmells

RIGHTS_SOCIETY_TRANSLATE = str.maketrans({'.': None, ' ': None, '•': None})

# some values that are not the actual data, but are metadata describing
# something about the SID codes (readable, missing, and so on) or about
# actions that need to be taken.
SID_IGNORE = set(['none', 'none?', 'none (?)', '(none)', '-none-', '[none]', '<none>', '\'none\'',
                  'none.', 'non', 'nond', 'none found', 'none or hidden', 'none given', 'not',
                  'not present', '(not present)', '[not present]', '<not present>',
                  'not present or not entered', '[not yet identified]', 'nothing',
                  'none / [missing]', 'missing', '(missing)', '?missing?', '"missing"',
                  '[missing]', '(missing info)', '[missing data]', '[missing or not entered]',
                  'missing entry', 'not available', '(not available)', '[not available]', 'not found',
                  '(not found)', '[not found]', '(not found on cd)', 'missing / not found',
                  '[indecipherable]', '(indistinguishable)', 'not known', 'unknown', '(unknown)',
                  '[unknown]', 'unk', 'not on disc', 'not visible', '(not visible)', '(not visble)',
                  '[not visible]', 'not visible/present', 'none or not visible',
                  'not visible on both cds', 'not visible (black cd)', 'not visable',
                  'none visible', '[none visible]', 'non visible', '[no code visible]',
                  '[none recorded]', '[none or missing]', 'none seen', '[none seen]', '[not seen]',
                  'not registered', 'none detected', 'none entered', 'not entered',
                  '[not entered]', '(not entered', '(not entered)', '[nothing entered]', 'not enterd',
                  'none or not entered', '(none or not entered)', '[none or not entered]',
                  'not entered / none', 'not entered or none', '(not entered or none)',
                  '[not entered/none]', '... not entered ...', '[to be entered]',
                  'not entered or not present', 'need to be entered',
                  'to be confirmed', '[?]', '[? ?]', '?', '??', '???', '????', '???????',
                  '(???)', 'no', 'not recorded', '[not recorded]', 'not supplied', '(not supplied)',
                  '[not supplied]', 'none supplied', 'unreadable', '[unreadable]', '(unreadable)',
                  'unreadable/too small', 'none or unreadable', 'nil', 'not given',
                  '(not given)', '[not given]', 'not inserted', '(not inserted)', '[not inserted]',
                  'not added', '(not added)', '[not added]', '[not added yet]',
                  '(to be added by another user)', 'none cited', 'not provided', '(not provided)',
                  'not stated', '[not stated]', 'not submitted', '[not submitted]',
                  '[not submittted]', '(not apparent)', '[not apparent]', '<not apparent>',
                  'none apparent', 'apparently none', 'not legible', '[not legible]', 'illegible',
                  '[illegible]', 'no sid', 'no sid code', 'no sid codes', 'no mastering sid code',
                  'not detectable', 'none or not detectable', '[not discernable]', 'not readable',
                  '(not readable)', '[not readable]', '[none/not readable]', '[none / not readable]',
                  'not readable (to small)', 'not clearly readable', 'can not read',
                  '[not reported]', 'no code', '[no code]', '(empty)', '[empty]', 'cannot locate',
                  'to be completed', 'obscured', 'invisible', '[not yet identified]',
                  'unidentified', 'not specified', 'no specified', 'not included', 'not noted',
                  '[not provided by user]', 'not shown', 'still missing', 'none stated', 'absent',
                  '[absent]', 'n/a', 'undetermined', '(doesnt have one)', 'non-existend',
                  'no mould', 'no mould sid', 'no mould sid code', '(no mould sid code)',
                  '[no mould sid code]', '"no mould sid code"', 'no mould sid-code',
                  'no mould code', '(no mould code)', 'no ifpi', 'no ifpi code', 'unstated',
                  '[blank]', 'unable to read', 'can\'t find', 'can\'t find it',
                  'no code discernible', 'vacant', '[none observed]', 'indistinct',
                  'information missing', 'no information', '(too faint to see)', 'without sid',
                  'There is something on the innermost edge but it is unreadable'])

SID_INVALID_FORMATS = set(['Vinyl', 'Cassette', 'Shellac', 'File',
                           'VHS', 'DCC', 'Memory Stick', 'Edison Disc'])

SPARS_TRANSLATE = str.maketrans({'.': None, ' ': None, '•': None, '·': None,
                                 '∙': None, '᛫': None, '[': None, ']': None,
                                 '-': None, '|': None, '/': None, '\\': None})

# Translation table for SID codes as some people
# insist on using ƒ/⨍ instead of f or ρ/ƥ instead of p
SID_TRANSLATE = str.maketrans({' ': None, '-': None,
                              '⨍': 'f', 'ƒ': 'f',
                              'ρ': 'p', 'ƥ': 'p'})

# grab the current year. Make sure to set the clock of your machine
# to the correct date or use NTP!
currentyear = datetime.datetime.utcnow().year

@dataclass
class CleanupConfig:
    '''Default cleanup configuration'''
    artist: bool = True
    asin: bool = True
    cd_plus_g: bool = True
    creative_commons: bool = False
    credits: bool = False
    czechoslovak_dates: bool = True
    czechoslovak_spelling: bool = True
    debug: bool = False
    deposito_legal: bool = True
    greek_license: bool = True
    indian_pkd: bool = True
    isrc: bool = True
    label_code: bool = True
    label_name: bool = True
    labels: bool = True
    manufacturing_plants: bool = True
    mastering_sid: bool = True
    matrix: bool = True
    month_valid: bool = False
    mould_sid: bool = True
    report_all: bool = False
    rights_society: bool = True
    spars: bool = True
    tracklisting: bool = True
    url_in_html: bool = True
    year_valid: bool = False

# a class with a handler for the SAX parser
class DiscogsHandler():
    def __init__(self, config_settings):
        # many default settings
        self.inrole = False
        self.inother = False
        self.indeposito = False
        self.inbarcode = False
        self.inasin = False
        self.inisrc = False
        self.inmouldsid = False
        self.inmatrix = False
        self.intracklist = False
        self.invideos = False
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
        self.formattexts = set()
        self.iscd = False
        self.depositofound = False
        self.labels = []
        self.config = config_settings
        self.contentbuffer = ''
        if self.config['check_credits']:
            creditsfile = open(self.config['creditsfile'], 'r')
            self.credits = set(map(lambda x: x.strip(), creditsfile.readlines()))
            creditsfile.close()

    # startElement() is called every time a new XML element is parsed
    def startElement(self, name, attrs):
        # first process the contentbuffer of the previous
        # element that was stored.
        if self.ingenre:
            self.genres.add(self.contentbuffer)
        if self.config['check_spelling_cs']:
            if self.country == 'Czechoslovakia' or self.country == 'Czech Republic':
                # People use 0x115 instead of 0x11B, which look very similar
                # but 0x115 is not valid in the Czech alphabet. Check for all
                # data except the YouTube playlist.
                # https://www.discogs.com/group/thread/757556
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
                    if '[' not in roledata:
                        roles = map(lambda x: x.strip(), roledata.split(','))
                        for role in roles:
                            if role == '':
                                continue
                            if role not in self.credits:
                                self.count += 1
                                print('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (self.count, role, str(self.release)))
                                sys.stdout.flush()
                    else:
                        # sometimes there is an additional description
                        # in the role in between [ and ]
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
                                    # ugly hack because sometimes the extra
                                    # data between [ and ] appears halfway the
                                    # words in a role, sigh.
                                    if role == 'By':
                                        continue
                                    if role not in self.credits:
                                        self.count += 1
                                        print('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (self.count, role, str(self.release)))
                                        sys.stdout.flush()
                                        continue
        elif self.indescription:
            if self.indescriptions:
                if 'Styrene' in self.contentbuffer:
                    pass
        elif self.inartistid:
            if self.config['check_artist']:
                if self.contentbuffer == '0':
                    self.count += 1
                    print('%8d -- Artist not in database: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                    sys.stdout.flush()
                    self.noartist = True
                else:
                    self.noartist = False
                # TODO: check for genres, as No Artist is
                # often confused with Unknown Artist
                #if self.contentbuffer == '118760':
                #    if len(self.genres) != 0:
                #        print("https://www.discogs.com/artist/%s" % self.contentbuffer, "https://www.discogs.com/release/%s" % str(self.release))
                #        print(self.genres)
                #        sys.exit(0)
                self.artists.add(self.contentbuffer)
        elif self.incompanyid:
            if self.config['check_labels']:
                if self.year is not None:
                    # check for:
                    # https://www.discogs.com/label/205-Fontana
                    # https://www.discogs.com/label/7704-Philips
                    if self.contentbuffer == '205':
                        if self.year < 1957:
                            self.count += 1
                            print('%8d -- Label (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
                    elif self.contentbuffer == '7704':
                        if self.year < 1950:
                            self.count += 1
                            print('%8d -- Label (wrong year %s): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
            if self.config['check_plants']:
                if self.year is not None:
                    # check for:
                    # https://www.discogs.com/label/358102-PDO-USA
                    # https://www.discogs.com/label/360848-PMDC-USA
                    # https://www.discogs.com/label/266782-UML
                    # https://www.discogs.com/label/381697-EDC-USA
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

                    # check for
                    # https://www.discogs.com/label/358025-PDO-Germany
                    # https://www.discogs.com/label/342158-PMDC-Germany
                    # https://www.discogs.com/label/331548-Universal-M-L-Germany
                    # https://www.discogs.com/label/384133-EDC-Germany
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

                    # https://www.discogs.com/label/265455-PMDC
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

                    # check for:
                    #
                    # Dureco:
                    # -------
                    # https://www.discogs.com/label/7207-Dureco
                    # https://dureco.wordpress.com/2014/12/09/opening-cd-fabriek-weesp/
                    # https://www.anderetijden.nl/aflevering/141/De-komst-van-het-schijfje (starting 22:25)
                    # https://books.google.nl/books?id=yyQEAAAAMBAJ&pg=RA1-PA37&lpg=RA1-PA37&dq=dureco+CDs+1987&source=bl&ots=cwc3WPM3Nw&sig=t0man_qWguylE9HEyqO39axo8kM&hl=nl&sa=X&ved=0ahUKEwjdme-xxcTZAhXN26QKHURgCJc4ChDoAQg4MAE#v=onepage&q&f=false
                    # https://www.youtube.com/watch?v=laDLvlj8tIQ
                    # https://krantenbankzeeland.nl/issue/pzc/1987-09-19/edition/0/page/21
                    #
                    # Since Dureco was also a distributor there are
                    # sometimes false positives
                    #
                    # Microservice:
                    # -------------
                    # https://www.discogs.com/label/300888-Microservice-Microfilmagens-e-Reprodu%C3%A7%C3%B5es-T%C3%A9cnicas-Ltda
                    #
                    # MPO:
                    # ----
                    # https://www.discogs.com/label/56025-MPO
                    #
                    # Nimbus:
                    # ------
                    # https://www.discogs.com/label/93218-Nimbus
                    #
                    # Mayking:
                    # -------
                    # https://www.discogs.com/label/147881-Mayking
                    #
                    # EMI Uden:
                    # --------
                    # https://www.discogs.com/label/266256-EMI-Uden
                    #
                    # WEA Mfg Olyphant:
                    # -----------------
                    # https://www.discogs.com/label/291934-WEA-Mfg-Olyphant
                    #
                    # Opti.Me.S:
                    # ----------
                    # https://www.discogs.com/label/271323-OptiMeS
                    #
                    # Format: (plant id, year production started, label name)
                    plants = [('7207', 1987, 'Dureco'), ('300888', 1987, 'Microservice'), ('56025', 1984, 'MPO'), ('93218', 1984, 'Nimbus'), ('147881', 1985, 'Mayking'), ('266256', 1989, 'EMI Uden'), ('291934', 1996, 'WEA Mfg Olyphant'), ('271323', 1986, 'Opti.Me.S')]
                    for pl in plants:
                        if self.contentbuffer == pl[0]:
                            if 'CD' in self.formattexts:
                                if self.year < pl[1]:
                                    self.count += 1
                                    print('%8d -- Pressing plant %s (possibly wrong year %s): https://www.discogs.com/release/%s' % (self.count, pl[2], self.year, str(self.release)))
                                    break

        if self.intracklist and self.inposition:
            '''
            # https://en.wikipedia.org/wiki/Phonograph_record#Microgroove_and_vinyl_era
            if 'Vinyl' in self.formattexts:
                if self.year is not None:
                    if self.year < 1948:
                        self.count += 1
                        print('%8d -- Impossible year (%d): https://www.discogs.com/release/%s' % (self.count, self.year, str(self.release)))
            '''
            if self.config['check_tracklisting']:
                if self.tracklistcorrect:
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

        # now reset some values
        self.incountry = False
        self.inrole = False
        self.inother = False
        self.inbarcode = False
        self.inasin = False
        self.inisrc = False
        self.inmouldsid = False
        self.inmatrix = False
        self.indeposito = False
        self.indescription = False
        self.intitle = False
        self.ingenre = False
        self.inposition = False
        self.contentbuffer = ''
        if not self.incompany:
            self.incompanyid = False
        self.inartistid = False
        if name == "release":
            # new release entry, so reset many fields
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
            self.formattexts = set()
            self.artists = set()
            self.labels = []
            self.formatmaxqty = 0
            self.genres = set()
            self.tracklistpositions = set()
            self.isrcpositions = set()
            self.isrcseen = set()
            for (k, v) in attrs.items():
                if k == 'id':
                    self.release = v
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
        elif name == 'role':
            self.inrole = True
        elif name == 'label':
            for (k, v) in attrs.items():
                if k == 'name':
                    labelname = v
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
                            if discogssmells.labelcodere.match(catno) is not None:
                                self.count += 1
                                self.prev = self.release
                                print('%8d -- Possible Label Code (in Catalogue Number): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                                return
                    if self.config['check_deposito']:
                        # now check for D.L.
                        dlfound = False
                        for d in discogssmells.depositores:
                            result = d.search(catno)
                            if result is not None:
                                for depositovalre in discogssmells.depositovalres:
                                    if depositovalre.search(catno) is not None:
                                        dlfound = True
                                        break

                        if dlfound:
                            self.count += 1
                            self.prev = self.release
                            print('%8d -- Possible Depósito Legal (in Catalogue Number): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                            return
            self.labels.append((labelname, catno))
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
        elif name == 'description':
            self.indescription = True
        elif name == 'identifier':
            isdeposito = False
            attritems = dict(attrs.items())
            if 'type' in attritems:
                v = attritems['type']
                if v == 'Depósito Legal':
                    self.indeposito = True
                    self.depositofound = True
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
                        if self.year is not None:
                            if 'MFG BY CINRAM' in v and '#' in v and 'USA' not in v:
                                cinramres = re.search('#(\d{2})', v)
                                if cinramres is not None:
                                    cinramyear = int(cinramres.groups()[0])
                                    # correct the year. This won't work correctly after 2099.
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
                                # https://www.discogs.com/label/277449-PO-Pallas
                                pallasres = re.search('P\+O[–-]\d{4,5}[–-][ABCD]\d?\s+\d{2}[–-](\d{2})', v)
                                if pallasres is not None:
                                    pallasyear = int(pallasres.groups()[0])
                                    # correct the year. This won't work correctly after 2099.
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

                            # just check a few other possibilities of
                            # possible SPARS codes
                            if tmpspars in discogssmells.validsparscodes:
                                self.count += 1
                                self.prev = self.release
                                print('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                                return
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
                    if self.country == 'Spain':
                        if self.config['check_deposito'] and not self.depositofound:
                            for depositovalre in discogssmells.depositovalres:
                                if depositovalre.match(v.lower()) is not None:
                                    self.count += 1
                                    self.prev = self.release
                                    print('%8d -- Depósito Legal (in Barcode): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                                    return
                if self.inasin:
                    if self.config['check_asin']:
                        # temporary hack, move to own configuration option
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
                        # Check the length of ISRC fields. According to the
                        # specifications these should be 12 in length. Some
                        # ISRC identifiers that have been recorded in the
                        # database cover a range of tracks. These will be
                        # reported as wrong ISRC codes. It is unclear what
                        # needs to be done with those.
                        # first get rid of cruft
                        isrc_tmp = v.strip().upper()
                        if isrc_tmp.startswith('ISRC'):
                            isrc_tmp = isrc_tmp.split('ISRC')[-1].strip()
                        if isrc_tmp.startswith('CODE'):
                            isrc_tmp = isrc_tmp.split('CODE')[-1].strip()

                        # Chinese ISRC, see https://www.discogs.com/forum/thread/799845
                        if '/A.J6' in isrc_tmp:
                            isrc_tmp = isrc_tmp.rsplit('/', 1)[0].strip()

                        # replace a few characters
                        isrc_tmp = isrc_tmp.replace('-', '')
                        isrc_tmp = isrc_tmp.replace(' ', '')
                        isrc_tmp = isrc_tmp.replace('.', '')
                        isrc_tmp = isrc_tmp.replace(':', '')
                        isrc_tmp = isrc_tmp.replace('–', '')
                        if len(isrc_tmp) != 12:
                            self.count += 1
                            self.prev = self.release
                            print('%8d -- ISRC (wrong length): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                            sys.stdout.flush()
                            return
                        else:
                            if isrc_tmp in self.isrcseen:
                                self.count += 1
                                self.prev = self.release
                                print('%8d -- ISRC (duplicate %s): https://www.discogs.com/release/%s' % (self.count, isrc_tmp, str(self.release)))
                                sys.stdout.flush()
                            self.isrcseen.add(isrc_tmp)
                            isrcres = re.match("\w{5}(\d{2})\d{5}", isrc_tmp)
                            if isrcres is None:
                                self.count += 1
                                self.prev = self.release
                                print('%8d -- ISRC (wrong format): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                                sys.stdout.flush()
                                return
                            if self.year is not None:
                                isrcyear = int(isrcres.groups()[0])
                                if isrcyear < 100:
                                    # correct the year. This won't work
                                    # correctly after 2099.
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
                if self.country == 'India':
                    if self.config['check_pkd']:
                        if 'pkd' in v.lower() or "production date" in v.lower():
                            if self.year is not None:
                                # try a few variants
                                pkdres = re.search("\d{1,2}/((?:19|20)?\d{2})", v)
                                if pkdres is not None:
                                    pkdyear = int(pkdres.groups()[0])
                                    if pkdyear < 100:
                                        # correct the year. This won't work correctly after 2099.
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
                    # People use 0x115 instead of 0x11B, which look very
                    # similar but 0x115 is not valid in the Czech alphabet.
                    # https://www.discogs.com/group/thread/757556
                    if self.country == 'Czechoslovakia' or self.country == 'Czech Republic':
                        if chr(0x115) in attrvalue or chr(0x115) in self.description:
                            self.count += 1
                            print('%8d -- Czech character (0x115): https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                if self.config['check_creative_commons']:
                    if 'creative commons' in self.description:
                        self.count += 1
                        print('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (self.count, str(self.release)))
                # squash repeated spaces
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
                            print('%8d -- ISRC Code (description reuse %s): https://www.discogs.com/release/%s' % (self.count, self.description.strip(), str(self.release)))
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
                            if result is not None:
                                found = True
                                break

                        # sometimes the depósito value itself can be
                        # found in the free text field
                        if not found:
                            for depositovalre in discogssmells.depositovalres:
                                deposres = depositovalre.match(self.description)
                                if deposres is not None:
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
                            if self.year is not None:
                                # try a few variants
                                pkdres = re.search("\d{1,2}/((?:19|20)?\d{2})", attrvalue)
                                if pkdres is not None:
                                    pkdyear = int(pkdres.groups()[0])
                                    if pkdyear < 100:
                                        # correct the year. This won't work correctly after 2099.
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
                        # config hack, needs to be in its own configuration option
                        strict_cs = False
                        if 'date' in self.description:
                            if self.year is not None:
                                manufacturing_date_res = re.search("(\d{2})\s+\d$", attrvalue.rstrip())
                                if manufacturing_date_res is not None:
                                    manufacturing_year = int(manufacturing_date_res.groups()[0])
                                    if manufacturing_year < 100:
                                        manufacturing_year += 1900
                                        if manufacturing_year > self.year:
                                            self.count += 1
                                            self.prev = self.release
                                            print("%8d -- Czechoslovak manufacturing date (release year wrong): https://www.discogs.com/release/%s" % (self.count, str(self.release)))
                                        # possibly this check makes sense, but not always
                                        elif manufacturing_year < self.year and strict_cs:
                                            self.count += 1
                                            self.prev = self.release
                                            print("%8d -- Czechoslovak manufacturing date (release year possibly wrong): https://www.discogs.com/release/%s" % (self.count, str(self.release)))

                elif self.country == 'Greece':
                    if self.config['check_greek_license_number']:
                        if "license" in self.description.strip() and self.year is not None:
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
                # debug code to print descriptions that were skipped.
                # Useful to find misspellings of various fields
                if self.config['debug']:
                    print(self.description, self.release)
                sys.stdout.flush()

    def characters(self, content):
        self.contentbuffer += content

def print_error(counter, reason, release_id):
    '''Helper method for printing errors'''
    print(f'{counter: 8} -- {reason}: https://www.discogs.com/release/{release_id}')
    sys.stdout.flush()

def check_spars(value, year):
    '''Helper method for checking SPARS codes'''
    wrong_spars = False
    errors = []

    # check if the code is valid
    if value not in discogssmells.validsparscodes:
        wrong_spars = True
        errors.append(f'Invalid SPARS: {value}')

    for s in value:
        if ord(s) > 256:
            wrong_spars = True
            errors.append(f'wrong character set: {value}')
            break

    if not wrong_spars:
        if year is not None:
            if year < 1984:
                errors.append(f"impossible year: {year}")
    return errors

@click.command(short_help='process BANG result files and output ELF graphs')
@click.option('--config-file', '-c', 'cfg', required=True, help='configuration file', type=click.File('r'))
@click.option('--datadump', '-d', 'datadump', required=True, help='discogs data dump file', type=click.Path(exists=True))
def main(cfg, datadump):
    config = configparser.ConfigParser()

    try:
        config.read_file(cfg)
    except Exception:
        print("Cannot read configuration file", file=sys.stderr)
        sys.exit(1)

    # process the configuration file and store settings.
    # Most of the defaults (but not all!) are set to 'True'
    config_settings = CleanupConfig()

    for section in config.sections():
        if section == 'cleanup':
            # store settings for depósito legal checks
            try:
                config_settings.deposito_legal = config.getboolean(section, 'deposito')
            except:
                pass

            # store settings for rights society checks
            try:
                config_settings.rights_society = config.getboolean(section, 'rights_society')
            except:
                pass

            # store settings for label code checks
            try:
                config_settings.label_code = config.getboolean(section, 'label_code')
            except:
                pass

            # store settings for label name checks
            try:
                config_settings.label_name = config.getboolean(section, 'label_name')
            except:
                pass

            # store settings for ISRC checks
            try:
                config_settings.isrc = config.getboolean(section, 'isrc')
            except:
                pass

            # store settings for ASIN checks
            try:
                config_settings.asin = config.getboolean(section, 'asin')
            except:
                pass

            # store settings for mastering SID checks
            try:
                config_settings.mastering_sid = config.getboolean(section, 'mastering_sid')
            except:
                pass

            # store settings for mould SID checks
            try:
                config_settings.mould_sid = config.getboolean(section, 'mould_sid')
            except:
                pass

            # store settings for SPARS Code checks
            try:
                config_settings.spars = config.getboolean(section, 'spars')
            except:
                pass

            # store settings for Indian PKD checks
            try:
                config_settings.indian_pkd = config.getboolean(section, 'pkd')
            except:
                pass

            # store settings for Greek license number checks
            try:
                config_settings.greek_license = config.getboolean(section, 'greek_license_number')
            except:
                pass

            # store settings for CD+G checks
            try:
                config_settings.cd_plus_g = config.getboolean(section, 'cdg')
            except:
                pass

            # store settings for Matrix checks
            try:
                config_settings.matrix = config.getboolean(section, 'matrix')
            except:
                pass

            # store settings for label checks
            try:
                config_settings.labels = config.getboolean(section, 'labels')
            except:
                pass

            # store settings for manufacturing plant checks
            try:
                config_settings.manufacturing_plants = config.getboolean(section, 'plants')
            except:
                pass

            # check for Czechoslovak manufacturing dates
            try:
                config_settings.czechoslovak_dates = config.getboolean(section, 'manufacturing_date_cs')
            except:
                pass

            # check for Czechoslovak and Czech spelling
            # (0x115 used instead of 0x11B)
            try:
                config_settings.czechoslovak_spelling = config.getboolean(section, 'spelling_cs')
            except:
                pass

            # store settings for tracklisting checks, default True
            try:
                config_settings.tracklisting = config.getboolean(section, 'tracklisting')
            except:
                pass

            # store settings for artists, default True
            try:
                config_settings.artist = config.getboolean(section, 'artist')
            except:
                pass

            # store settings for credits list checks
            config_settings.credits = False
            try:
                if config.get(section, 'credits') == 'yes':
                    creditsfile = config.get(section, 'creditsfile')
                    if os.path.exists(creditsfile):
                        # TODO: fix
                        config_settings.creditsfile = creditsfile
                        config_settings.credits = True
            except:
                pass

            # store settings for URLs in Notes checks
            try:
                config_settings.url_in_html = config.getboolean(section, 'html')
            except:
                pass

            # month is 00 check: default is False
            try:
                config_settings.month_valid = config.getboolean(section, 'month')
            except:
                pass

            # year is wrong check: default is False
            try:
                config_settings.year_valid = config.getboolean(section, 'year')
            except:
                pass

            # reporting all: default is False
            try:
                config_settings.report_all = config.getboolean(section, 'reportall')
            except:
                pass

            # debug: default is False
            try:
                config_settings.debug = config.getboolean(section, 'debug')
            except:
                pass

            # report creative commons references: default is False
            try:
                config_settings.creative_commons = config.getboolean(section, 'creative_commons')
            except:
                pass

    # keep a mapping for the 'identifiers' item, detailing which
    # item belongs where
    identifier_mapping = {'barcode', 'Barcode'}

    try:
        with gzip.open(datadump, "rb") as dumpfile:
            counter = 1
            for event, element in et.iterparse(dumpfile):
                if element.tag == 'release':
                    # first see if a release is worth looking at
                    status = element.get('status')
                    if status in ['Deleted', 'Draft', 'Rejected']:
                        continue

                    # store the release id
                    release_id = element.get('id')

                    # then store various things about the release
                    country = ""
                    deposito_found = False
                    year = None
                    formats = set()
                    num_formats = 0
                    is_cd = False

                    # and process the different elements
                    for child in element:
                        if child.tag == 'country':
                            country = child.text
                        elif child.tag == 'formats':
                            for release_format in child:
                                current_format = None
                                for (key, value) in release_format.items():
                                    if key == 'name':
                                        if value == 'CD':
                                            is_cd = True
                                        formats.add(value)
                                        current_format = value
                                    elif key == 'qty':
                                        if num_formats == 0:
                                            num_formats = max(num_formats, int(value))
                                        else:
                                            num_formats += int(value)
                                    elif key == 'text':
                                        if value != '':
                                            value_lower = value.lower().strip()
                                            if config_settings.spars:
                                                tmpspars = value_lower
                                                for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
                                                    tmpspars = tmpspars.replace(s, '')
                                                if tmpspars in discogssmells.validsparscodes:
                                                    print_error(counter, "Possible SPARS Code (in Format)", release_id)
                                                    counter += 1
                                            if config_settings.label_code:
                                                if value_lower.startswith('lc'):
                                                    if discogssmells.labelcodere.match(value_lower) is not None:
                                                        print_error(counter, "Possible Label Code (in Format)", release_id)
                                                        counter += 1
                                            if config_settings.cd_plus_g:
                                                if value_lower == 'cd+g':
                                                    print_error(counter, 'CD+G (in Format)', release_id)
                                                    counter += 1
                                            if value_lower == 'DMM':
                                                if current_format != 'Vinyl':
                                                    print_error(f'DMM ({current_format}, in Format)', release_id)
                                                    counter += 1

                        elif child.tag == 'identifiers':
                            # Here things get very hairy, as every check
                            # potentially has to be done multiple times: once
                            # in the 'correct' field (example: rights society
                            # in a 'Rights Society' field) and then in all the
                            # other fields as well.
                            #
                            # The checks in the 'correct' field tend to be more
                            # thorough, as the chances that this is indeed the
                            # correct field are high.
                            #
                            # Sometimes the "description" attribute needs to be
                            # checked as well as people tend to hide information
                            # there too.
                            for identifier in child:
                                identifier_type = identifier.get('type')

                                # Depósito Legal, only check for releases from Spain
                                if country == 'Spain':
                                    if config_settings.deposito_legal:
                                        if identifier_type == 'Depósito Legal':
                                            deposito_found = True
                                            value = identifier.get('value')
                                            if value.endswith('.'):
                                                print_error(counter, "Depósito Legal (formatting)", release_id)
                                                counter += 1

                                            if year is not None:
                                                # now try to find the year
                                                deposito_year = None
                                                year_value = value.strip()
                                                if year_value.endswith('℗'):
                                                    print_error(counter, "Depósito Legal (formatting, has ℗)", release_id)
                                                    counter += 1
                                                    # ugly hack, remove ℗ to make at least be able to do some sort of check
                                                    year_value = year_value.rsplit('℗', 1)[0].strip()

                                                # several separators seen in the DL codes,
                                                # including some Unicode ones.
                                                # TODO: rewrite/improve
                                                for sep in ['-', '–', '/', '.', ' ', '\'', '_']:
                                                    try:
                                                        deposito_year_text = year_value.rsplit(sep, 1)[-1]
                                                        if sep == '.' and len(deposito_year_text) == 3:
                                                            continue
                                                        if '.' in deposito_year_text:
                                                            deposito_year_text = deposito_year_text.replace('.', '')
                                                        deposito_year = int(deposito_year_text)
                                                        if deposito_year < 100:
                                                            # correct the year. This won't work correctly after 2099.
                                                            if deposito_year <= currentyear - 2000:
                                                                deposito_year += 2000
                                                            else:
                                                                deposito_year += 1900
                                                        break
                                                    except ValueError:
                                                        pass

                                                # TODO, also allow (year), example: https://www.discogs.com/release/265497
                                                if deposito_year is not None:
                                                    if deposito_year < 1900:
                                                        print_error(counter, f"Depósito Legal (impossible year: {deposito_year})", release_id)
                                                        counter += 1
                                                    elif deposito_year > currentyear:
                                                        print_error(counter, f"Depósito Legal (impossible year: {deposito_year})", release_id)
                                                        counter += 1
                                                    elif year < deposito_year:
                                                        print_error(counter, "Depósito Legal (release date earlier)", release_id)
                                                        counter += 1
                                                else:
                                                    print_error(counter, "Depósito Legal (year not found)", release_id)
                                                    counter += 1
                                        else:
                                            value = identifier.get('value')
                                            for dls in ['D.L.', 'Depósito']:
                                                if value.startswith(dls):
                                                    print_error(counter, f"Depósito Legal (in {identifier_type})", release_id)
                                                    counter += 1

                                        # check for a DL in the description field

                                # Label Code
                                if config_settings.label_code:
                                    value = identifier.get('value').lower()
                                    if identifier_type == 'Label Code':
                                        # check how many people use 'O' instead of '0'
                                        if value.startswith('lc'):
                                            if 'O' in value:
                                                print_error(counter, "Spelling error (in Label Code)", release_id)
                                                counter += 1
                                        if discogssmells.labelcodere.match(value) is None:
                                            print_error(counter, "Label Code (value)", release_id)
                                            counter += 1
                                    else:
                                        if value.startswith('lc'):
                                            if discogssmells.labelcodere.match(value) is not None:
                                                print_error(counter, f"Label Code (in {identifier_type})", release_id)
                                                counter += 1

                                # Mastering SID Code
                                if config_settings.mastering_sid:
                                    if identifier_type == 'Mastering SID Code':
                                        value = identifier.get('value').strip()
                                        value_lower = identifier.get('value').lower().strip()
                                        if value_lower not in SID_IGNORE:
                                            # cleanup first for not so heavy formatting booboos
                                            master_sid_tmp = value_lower.translate(SID_TRANSLATE)
                                            res = discogssmells.masteringsidre.match(master_sid_tmp)
                                            if res is None:
                                                print_error(counter, f'Mastering SID Code (value: {value})', release_id)
                                                counter += 1
                                            else:
                                                # rough check to find SID codes for formats
                                                # other than CD/CD-like
                                                if len(formats) == 1:
                                                    for fmt in SID_INVALID_FORMATS:
                                                        if fmt in formats:
                                                            print_error(counter, f'Mastering SID Code (Wrong Format: {fmt})', release_id)
                                                            counter += 1
                                                if year is not None:
                                                    if year < 1993:
                                                        print_error(counter, f'Mastering SID Code (wrong year: {year})', release_id)
                                                        counter += 1

                                # Mould SID Code
                                # temporary hack, move to own configuration option
                                mould_sid_strict = False
                                if config_settings.mould_sid:
                                    if identifier_type == 'Mould SID Code':
                                        value = identifier.get('value').strip()
                                        value_lower = identifier.get('value').lower().strip()
                                        if value_lower not in SID_IGNORE:
                                            # cleanup first for not so heavy formatting booboos
                                            mould_sid_tmp = value_lower.translate(SID_TRANSLATE)
                                            res = discogssmells.mouldsidre.match(mould_sid_tmp)
                                            if res is None:
                                                print_error(counter, f'Mould SID Code (value: {value})', release_id)
                                                counter += 1
                                            else:
                                                if mould_sid_strict:
                                                    mould_split = mould_sid_tmp.split('ifpi', 1)[-1]
                                                    for ch in ['i', 'o', 's', 'q']:
                                                        if ch in mould_split[-2:]:
                                                            print_error(counter, 'Mould SID Code (strict value)', release_id)
                                                            counter += 1
                                                # rough check to find SID codes for formats
                                                # other than CD/CD-like
                                                if len(formats) == 1:
                                                    for fmt in SID_INVALID_FORMATS:
                                                        if fmt in formats:
                                                            print_error(counter, f'Mould SID Code (Wrong Format: {fmt})', release_id)
                                                            counter += 1
                                                if year is not None:
                                                    if year < 1993:
                                                        print_error(counter, f'Mould SID Code (wrong year: {year})', release_id)
                                                        counter += 1
                                # Rights Society
                                if config_settings.rights_society:
                                    value = identifier.get('value')
                                    value_upper = value.upper().translate(RIGHTS_SOCIETY_TRANSLATE)
                                    if identifier_type == 'Rights Society':
                                        if value_upper not in discogssmells.rights_societies:
                                            reported = False
                                            for r in discogssmells.rights_societies_wrong:
                                                if r in value_upper:
                                                    print_error(counter, f"Rights Society (possible wrong value: {r})", release_id)
                                                    counter += 1
                                                    reported = True
                                                    break

                                            if value_upper in discogssmells.rights_societies_wrong_char:
                                                print_error(counter, f"Rights Society (wrong character set: {value_upper})", release_id)
                                                counter += 1
                                                reported = True

                                            # TODO: fix this
                                            if not reported and False:
                                                print_error(counter, f"Rights Society (bogus value: {value})", release_id)
                                                counter += 1
                                    else:
                                        if value_upper in discogssmells.rights_societies:
                                            print_error(counter, f"Rights Society ('{value}' in {identifier_type})", release_id)
                                            counter += 1
                                # SPARS Code
                                if config_settings.spars:
                                    value = identifier.get('value')
                                    if identifier_type == 'SPARS Code':
                                        if value != 'none':
                                            # Sony format codes
                                            # https://www.discogs.com/forum/thread/339244
                                            # https://www.discogs.com/forum/thread/358285
                                            if value in ['CDC', 'CDM']:
                                                print_error(counter, f"Sony Format Code in SPARS ({value})", release_id)
                                                counter += 1
                                            else:
                                                # temporary list to store SPARS values to check
                                                spars_to_check = []

                                                value_lower = value.lower().strip()
                                                tmp_spars = value_lower

                                                # replace any delimiter that people might have used
                                                tmp_spars = tmp_spars.translate(SPARS_TRANSLATE)

                                                spars_is_split = False

                                                if len(tmp_spars) == 3:
                                                    spars_to_check.append(tmp_spars)
                                                else:
                                                    # instead of one SPARS code there might be multiple
                                                    for s in ['|', '/', ',', ' ', '&', '-', '+', '•']:
                                                        if s in value_lower:
                                                            split_spars = list(map(lambda x: x.strip(), value_lower.split(s)))
                                                            # check if every code has three characters
                                                            if len(list(filter(lambda x: len(x) == 3, split_spars))) != len(split_spars):
                                                                continue
                                                            spars_is_split = True
                                                            spars_to_check = split_spars
                                                            break

                                                    if not spars_is_split:
                                                        spars_to_check.append(tmp_spars)

                                                for sparscheck in spars_to_check:
                                                    errors = check_spars(sparscheck, year)
                                                    for error in errors:
                                                        print_error(counter, f"SPARS Code ({error})", release_id)
                                                        counter += 1
                                    else:
                                        if value.lower() in discogssmells.validsparscodes:
                                            print_error(counter, f"SPARS Code ({value}, in {identifier_type})", release_id)
                                            counter += 1
                        elif child.tag == 'notes':
                            #if '카지노' in child.text:
                            #    # Korean casino spam that used to pop up
                            #    # every once in a while.
                            #    print_error(counter, "Korean casino spam", release_id)
                            #    counter += 1
                            if country == 'Spain':
                                if config_settings.deposito_legal and not deposito_found:
                                    # sometimes "deposito legal" can be found
                                    # in the "notes" section.
                                    content_lower = child.text.lower()
                                    for d in discogssmells.depositores:
                                        result = d.search(content_lower)
                                        if result is not None:
                                            print_error(counter, "Depósito Legal (Notes)", release_id)
                                            counter += 1
                                            found = True
                                            break

                            # see https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-
                            if config_settings.url_in_html:
                                if '&lt;a href="http://www.discogs.com/release/' not in child.text:
                                    print_error(counter, "old link (Notes)", release_id)
                                    counter += 1
                            if config_settings.creative_commons:
                                cc_found = False
                                for cc in discogssmells.creativecommons:
                                    if cc in child.text:
                                        print_error(counter, f"Creative Commons reference ({cc})", release_id)
                                        counter += 1
                                        cc_found = True
                                        break

                                if not cc_found:
                                    if 'creative commons' in child.text.lower():
                                        print_error(counter, "Creative Commons reference", release_id)
                                        counter += 1

                        if child.tag == 'released':
                            if config_settings.month_valid:
                                monthres = re.search(r'-(\d+)-', child.text)
                                if monthres is not None:
                                    month_nr = int(monthres.groups()[0])
                                    if month_nr == 0:
                                        print_error(counter, "Month 00", release_id)
                                        counter += 1
                                    elif month_nr > 12:
                                        print_error(counter, f"Month impossible {month_nr}", release_id)
                                        counter += 1

                            if child.text != '':
                                try:
                                    year = int(child.text.split('-', 1)[0])
                                except ValueError:
                                    if config_settings.year_valid:
                                        print_error(counter, f"Year {child.text} invalid", release_id)
                                        counter += 1

                    # cleanup to reduce memory usage
                    element.clear()
    except Exception as e:
        print("Cannot open dump file", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
