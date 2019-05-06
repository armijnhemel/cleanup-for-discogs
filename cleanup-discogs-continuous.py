#!/usr/bin/env python3

# Tool to discover 'smells' in the Discogs data via the API. It downloads
# release data and flags releases that need to be fixed.
#
# The checks are (nearly) identical to cleanup-discogs.py
#
# The results that are printed by this script are by no means complete or accurate.
#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright 2017 - 2019 - Armijn Hemel for Tjaldur Software Governance Solutions

import sys
import os
import gzip
import re
import datetime
import time
import json
import subprocess
import argparse
import configparser
import tempfile

import requests
import discogssmells

# grab the current year. Make sure to set the clock of your machine
# to the correct date or use NTP!
currentyear = datetime.datetime.utcnow().year

# Since the API does not have a call to get the latest release that has been
# added to the database get it from the following webpage by scraping. This is ugly.
# https://www.discogs.com/search/?sort=date_added%2Cdesc&type=release
#
# The contents of this page are different depending on whether or not you are logged
# into the website. If you are not logged in, then it is a few hours behind.
def get_latest_release(headers):
    r = requests.get('https://api.discogs.com/database/search?type=release&sort=date_added', headers=headers)
    if r.status_code != 200:
        return

    # now parse the response
    responsejson = r.json()
    if not 'results' in responsejson:
        return

    return responsejson['results'][0]['id']


# convenience method to check if roles are valid
def checkrole(artist, release_id, credits):
    invalidroles = []
    if not '[' in artist['role']:
        roles = map(lambda x: x.strip(), artist['role'].split(','))
        for role in roles:
            if role == '':
                continue
            if not role in credits:
                invalidroles.append(role)
    else:
        # sometimes there is an additional description in the role in between [ and ]
        # This method is definitely not catching everything.
        rolesplit = artist['role'].split('[')
        for rs in rolesplit:
            if ']' in rs:
                rs_tmp = rs
                while ']' in rs_tmp:
                    rs_tmp = rs_tmp.split(']', 1)[1]
                roles = map(lambda x: x.strip(), rs_tmp.split(','))
                for role in roles:
                    if role == '':
                        continue
                    # ugly hack because sometimes the extra data between [ and ]
                    # appears halfway the words in a role, sigh.
                    if role == 'By':
                        continue
                    if not role in credits:
                        invalidroles.append(role)
    return invalidroles


# process the contents of a release
def processrelease(release, config_settings, count, credits, ibuddy, favourites):
    # only process entries that have a status of 'Accepted'
    if release['status'] == 'Rejected':
        return count
    elif release['status'] == 'Draft':
        return count
    elif release['status'] == 'Deleted':
        return count

    errormsgs = []

    # store some data that is used by multiple checks
    founddeposito = False
    year = None
    release_id = release['id']

    # check for favourite artist, if defined
    for artist in release['artists']:
        if artist['name'] in favourites:
            if ibuddy != None:
                ibuddy.executecommand('HEART:WINGSHIGH:RED:GO:SHORTSLEEP:NOHEART:WINGSLOW:GO:SHORTSLEEP:HEART:LEFT::WINGSHIGH::GO:SHORTSLEEP:NOHEART:RIGHT:GO:HEART:GO:BLUE:SHORTSLEEP:WINGSLOW:GO:SHORTSLEEP:RESET')
                ibuddy.reset()
            if config_settings['use_notify_send']:
                count += 1
                errormsgs.append('%8d -- Favourite Artist (%s): https://www.discogs.com/release/%s' % (count, artist['name'], str(release_id)))

    # check for misspellings of Czechoslovak and Czech releases
    # People use 0x115 instead of 0x11B, which look very similar but 0x115 is not valid
    # in the Czech alphabet. Check for all data except the YouTube playlist.
    # https://www.discogs.com/group/thread/757556
    # This is important for the following elements:
    # * tracklist (title, subtracks not supported yet)
    # * artist and extraartists (including extraartists in tracklist)
    # * notes
    # * BaOI identifiers (both value and description)
    if config_settings['check_spelling_cs']:
        if 'country' in release:
            if release['country'] == 'Czechoslovakia' or release['country'] == 'Czech Republic':
                for t in release['tracklist']:
                    if chr(0x115) in t['title']:
                        count += 1
                        errormsgs.append('%8d -- Czech character (0x115, tracklist: %s): https://www.discogs.com/release/%s' % (count, t['position'], str(release_id)))
                    if 'extraartists' in t:
                        for artist in t['extraartists']:
                            if chr(0x115) in artist['name']:
                                count += 1
                                errormsgs.append('%8d -- Czech character (0x115, artist name at: %s): https://www.discogs.com/release/%s' % (count, t['position'], str(release_id)))
                if 'artists' in release:
                    for artist in release['artists']:
                        if chr(0x115) in artist['name']:
                            count += 1
                            errormsgs.append('%8d -- Czech character (0x115, artist name: %s): https://www.discogs.com/release/%s' % (count, artist['name'], str(release_id)))
                if 'extraartists' in release:
                    for artist in release['extraartists']:
                        if chr(0x115) in artist['name']:
                            count += 1
                            errormsgs.append('%8d -- Czech character (0x115, artist name: %s): https://www.discogs.com/release/%s' % (count, artist['name'], str(release_id)))
                for i in release['identifiers']:
                    if chr(0x115) in i['value']:
                        count += 1
                        errormsgs.append('%8d -- Czech character (0x115, BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    if 'description' in i:
                        if chr(0x115) in i['description']:
                            count += 1
                            errormsgs.append('%8d -- Czech character (0x115, BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                if 'notes' in release:
                    if chr(0x115) in release['notes']:
                        count += 1
                        errormsgs.append('%8d -- Czech character (0x115, Notes): https://www.discogs.com/release/%s' % (count, str(release_id)))

    # check credit roles in three places:
    # 1. artists
    # 2. extraartists (release level)
    # 3. extraartists (track level)
    if 'check_credits' in config_settings:
        if config_settings['check_credits']:
            if 'artists' in release:
                for artist in release['artists']:
                    if 'role' in artist:
                        invalidroles = checkrole(artist, release_id, credits)
                        for role in invalidroles:
                            count += 1
                            errormsgs.append('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (count, role, str(release_id)))
            if 'extraartists' in release:
                for artist in release['extraartists']:
                    if 'role' in artist:
                        invalidroles = checkrole(artist, release_id, credits)
                        for role in invalidroles:
                            count += 1
                            errormsgs.append('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (count, role, str(release_id)))
            for t in release['tracklist']:
                if 'extraartists' in t:
                    for artist in t['extraartists']:
                        if 'role' in artist:
                            invalidroles = checkrole(artist, release_id, credits)
                            for role in invalidroles:
                                count += 1
                                errormsgs.append('%8d -- Role \'%s\' invalid: https://www.discogs.com/release/%s' % (count, role, str(release_id)))

    # check release month and year
    if 'released' in release:
        if config_settings['check_month']:
            if '-' in release['released']:
                monthres = re.search('-(\d+)-', release['released'])
                if monthres != None:
                    monthnr = int(monthres.groups()[0])
                    if monthnr == 0:
                        count += 1
                        errormsgs.append('%8d -- Month 00: https://www.discogs.com/release/%s' % (count, str(release_id)))
                    elif monthnr > 12:
                        count += 1
                        errormsgs.append('%8d -- Month impossible (%d): https://www.discogs.com/release/%s' % (count, monthnr, str(release_id)))
        try:
            year = int(release['released'].split('-', 1)[0])
            # TODO: check for implausible old years
        except ValueError:
            if config_settings['check_year']:
                count += 1
                errormsgs.append('%8d -- Year \'%s\' invalid: https://www.discogs.com/release/%s' % (count, release['released'], str(release_id)))

    # check the tracklist
    tracklistcorrect = True
    tracklistpositions = set()
    formattexts = set()
    if config_settings['check_tracklisting'] and len(release['formats']) == 1:
        formattext = release['formats'][0]['name']
        formattexts.add(formattext)
        formatqty = int(release['formats'][0]['qty'])
        for t in release['tracklist']:
            if tracklistcorrect:
                if formattext in ['Vinyl', 'Cassette', 'Shellac', '8-Track Cartridge']:
                    try:
                        int(t['position'])
                        count += 1
                        errormsgs.append('%8d -- Tracklisting (%s): https://www.discogs.com/release/%s' % (count, formattext, str(release_id)))
                        tracklistcorrect = False
                        break
                    except:
                        pass
                if formatqty == 1:
                    if t['position'].strip() != '' and t['position'].strip() != '-' and t['type_'] != 'heading' and t['position'] in tracklistpositions:
                        count += 1
                        errormsgs.append('%8d -- Tracklisting reuse (%s, %s): https://www.discogs.com/release/%s' % (count, formattext, t['position'], str(release_id)))
                    tracklistpositions.add(t['position'])

    # various checks for labels
    for l in release['labels']:
        # check for several identifiers being used as catalog numbers
        if 'catno' in l:
            if config_settings['check_label_code']:
                if l['catno'].lower().startswith('lc'):
                    falsepositive = False
                    # American releases on Epic (label 1005 in Discogs) sometimes start with LC
                    if l['id'] == 1005:
                        falsepositive = True
                    if not falsepositive:
                        if discogssmells.labelcodere.match(l['catno'].lower()) != None:
                            count += 1
                            errormsgs.append('%8d -- Possible Label Code (in Catalogue Number): https://www.discogs.com/release/%s' % (count, str(release_id)))
            if config_settings['check_deposito']:
                # now check for D.L.
                dlfound = False
                for d in discogssmells.depositores:
                    result = d.search(l['catno'])
                    if result != None:
                        for depositovalre in discogssmells.depositovalres:
                            if depositovalre.search(l['catno']) != None:
                                dlfound = True
                                break

                if dlfound:
                    count += 1
                    errormsgs.append('%8d -- Possible Depósito Legal (in Catalogue Number): https://www.discogs.com/release/%s' % (count, str(release_id)))
        if 'name' in l:
            if config_settings['check_label_name']:
                if l['name'] == 'London' and l['id'] == 26905:
                    count += 1
                    errormsgs.append('%8d -- Wrong label (London): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    pass
    '''
    if name == 'format':
        for (k,v) in attrs.items():
            if k == 'name':
                if v == 'CD':
                    self.iscd = True
                self.formattexts.add(v)
            elif k == 'qty':
                if self.formatmaxqty == 0:
                    self.formatmaxqty = max(self.formatmaxqty, int(v))
                else:
                    self.formatmaxqty += int(v)
    '''

    # various checks for the formats
    formattexts = set()
    for f in release['formats']:
        if 'descriptions' in f:
            if 'Styrene' in f['descriptions']:
                pass
        # store the names of the formats. This is useful later for SID code checks
        if 'name' in f:
            formattexts.add(f['name'])
        if 'text' in f:
            if f['text'] != '':
                if config_settings['check_spars_code']:
                    tmpspars = f['text'].lower().strip()
                    for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
                        tmpspars = tmpspars.replace(s, '')
                    if tmpspars in discogssmells.validsparscodes:
                        count += 1
                        errormsgs.append('%8d -- Possible SPARS Code (in Format): https://www.discogs.com/release/%s' % (count, str(release_id)))
                if config_settings['check_label_code']:
                    if f['text'].lower().startswith('lc'):
                        if discogssmells.labelcodere.match(f['text'].lower()) != None:
                            count += 1
                            errormsgs.append('%8d -- Possible Label Code (in Format): https://www.discogs.com/release/%s' % (count, str(release_id)))

    # walk through the BaOI identifiers
    for identifier in release['identifiers']:
        v = identifier['value']
        if config_settings['check_creative_commons']:
            if 'creative commons' in v.lower():
                count += 1
                errormsgs.append('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (count, str(release)))
            if 'description' in identifier:
                if 'creative commons' in identifier['description'].lower():
                    count += 1
                    errormsgs.append('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (count, str(release)))
        if config_settings['check_spars_code']:
            if identifier['type'] == 'SPARS Code':
                if v.lower() != "none":
                    # Sony format codes
                    # https://www.discogs.com/forum/thread/339244
                    # https://www.discogs.com/forum/thread/358285
                    if v == 'CDC' or v == 'CDM':
                        count += 1
                        errormsgs.append('%8d -- Sony Format Code in SPARS: https://www.discogs.com/release/%s' % (count, str(release_id)))
                    else:
                        tmpspars = v.lower().strip()
                        for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
                            tmpspars = tmpspars.replace(s, '')
                        if not tmpspars in discogssmells.validsparscodes:
                            count += 1
                            errormsgs.append('%8d -- SPARS Code (format): https://www.discogs.com/release/%s' % (count, str(release_id)))
            else:
                # first check the description free text field
                sparsfound = False
                if 'description' in identifier:
                    for spars in discogssmells.spars_ftf:
                        if spars in identifier['description'].lower():
                            sparsfound = True
                # then also check the value to see if there is a valid SPARS
                if v.lower() in discogssmells.validsparscodes:
                    sparsfound = True
                else:
                    if 'd' in v.lower():
                        tmpspars = v.strip()
                        for s in ['.', ' ', '•', '·', '[', ']', '-', '|', '/']:
                            tmpspars = tmpspars.replace(s, '')
                        if tmpspars in discogssmells.validsparscodes:
                            sparsfound = True
                # print error if some SPARS code reference was found
                if sparsfound:
                    count += 1
                    errormsgs.append('%8d -- SPARS Code (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
        if config_settings['check_label_code']:
            if identifier['type'] == 'Label Code':
                # check how many people use 'O' instead of '0'
                if v.lower().startswith('lc'):
                    if 'O' in identifier['value']:
                        errormsgs.append('%8d -- Spelling error in Label Code): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        sys.stdout.flush()
                if discogssmells.labelcodere.match(v.lower()) == None:
                    count += 1
                    errormsgs.append('%8d -- Label Code (value): https://www.discogs.com/release/%s' % (count, str(release_id)))
            else:
                if identifier['type'] == 'Rights Society':
                    if v.lower().startswith('lc'):
                        if discogssmells.labelcodere.match(v.lower()) != None:
                            count += 1
                            errormsgs.append('%8d -- Label Code (in Rights Society): https://www.discogs.com/release/%s' % (count, str(release_id)))
                elif identifier['type'] == 'Barcode':
                    if v.lower().startswith('lc'):
                        if discogssmells.labelcodere.match(v.lower()) != None:
                            count += 1
                            errormsgs.append('%8d -- Label Code (in Barcode): https://www.discogs.com/release/%s' % (count, str(release_id)))
                else:
                    if 'description' in identifier:
                        if identifier['description'].lower() in discogssmells.label_code_ftf:
                            count += 1
                            errormsgs.append('%8d -- Label Code: https://www.discogs.com/release/%s' % (count, str(release_id)))
        if config_settings['check_rights_society']:
            if identifier['type'] != 'Rights Society':
                foundrightssociety = False
                for r in discogssmells.rights_societies:
                    if v.replace('.', '') == r or v.replace(' ', '') == r:
                        count += 1
                        foundrightssociety = True
                        if identifier['type'] == 'Barcode':
                            errormsgs.append('%8d -- Rights Society (Barcode): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        else:
                            errormsgs.append('%8d -- Rights Society (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        break
                if not foundrightssociety and 'description' in identifier:
                    if identifier['description'].lower() in discogssmells.rights_societies_ftf:
                        count += 1
                        errormsgs.append('%8d -- Rights Society: https://www.discogs.com/release/%s' % (count, str(release_id)))

        # temporary hack, move to own configuration option
        asinstrict = False
        if config_settings['check_asin']:
            if identifier['type'] == 'ASIN':
                if not asinstrict:
                    tmpasin = v.strip().replace('-', '')
                else:
                    tmpasin = v
                if not len(tmpasin.split(':')[-1].strip()) == 10:
                    count += 1
                    errormsgs.append('%8d -- ASIN (wrong length): https://www.discogs.com/release/%s' % (count, str(release_id)))
            else:
                if 'description' in identifier:
                    if identifier['description'].lower().startswith('asin'):
                        count += 1
                        errormsgs.append('%8d -- ASIN (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
        if config_settings['check_isrc']:
            if identifier['type'] == 'ISRC':
                # Check the length of ISRC fields. According to the specifications these should
                # be 12 in length. Some ISRC identifiers that have been recorded in the database
                # cover a range of tracks. These will be reported as wrong ISRC codes. It is unclear
                # what needs to be done with those.
                # first get rid of cruft
                isrc_tmp = v.strip().upper()
                if isrc_tmp.startswith('ISRC'):
                    isrc_tmp = isrc_tmp.split('ISRC')[-1].strip()
                if isrc_tmp.startswith('CODE'):
                    isrc_tmp = isrc_tmp.split('CODE')[-1].strip()
                # replace a few characters
                isrc_tmp = isrc_tmp.replace('-', '')
                isrc_tmp = isrc_tmp.replace(' ', '')
                isrc_tmp = isrc_tmp.replace('.', '')
                isrc_tmp = isrc_tmp.replace(':', '')
                isrc_tmp = isrc_tmp.replace('–', '')
                if not len(isrc_tmp) == 12:
                    count += 1
                    errormsgs.append('%8d -- ISRC (wrong length): https://www.discogs.com/release/%s' % (count, str(release_id)))
            else:
                if 'description' in identifier:
                    if identifier['description'].lower().startswith('isrc'):
                        count += 1
                        errormsgs.append('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    elif identifier['description'].lower().startswith('issrc'):
                        count += 1
                        errormsgs.append('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    else:
                        for isrc in discogssmells.isrc_ftf:
                            if isrc in identifier['description'].lower():
                                count += 1
                                errormsgs.append('%8d -- ISRC Code (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
        if identifier['type'] == 'Barcode':
            pass

        # check depósito legal in BaOI
        if config_settings['check_deposito']:
            if 'country' in release:
                if release['country'] == 'Spain':
                    if identifier['type'] == 'Depósito Legal':
                        founddeposito = True
                        if v.strip().endswith('.'):
                            count += 1
                            errormsgs.append('%8d -- Depósito Legal (formatting): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        if year != None:
                            # now try to find the year
                            depositoyear = None
                            if v.strip().endswith('℗'):
                                count += 1
                                errormsgs.append('%8d -- Depósito Legal (formatting, has ℗): https://www.discogs.com/release/%s' % (count, str(release_id)))
                                # ugly hack, remove ℗ to make at least be able to do some sort of check
                                v = v.strip().rsplit('℗', 1)[0]
                            # several separators, including some Unicode ones
                            for sep in ['-', '–', '/', '.', ' ', '\'', '_']:
                                try:
                                    depositoyeartext = v.strip().rsplit(sep, 1)[-1]
                                    if sep == '.' and len(depositoyeartext) == 3:
                                        continue
                                    if '.' in depositoyeartext:
                                        depositoyeartext = depositoyeartext.replace('.', '')
                                    depositoyear = int(depositoyeartext)
                                    if depositoyear < 100:
                                        # correct the year. This won't work correctly after 2099.
                                        if depositoyear <= currentyear - 2000:
                                            depositoyear += 2000
                                        else:
                                            depositoyear += 1900
                                    break
                                except:
                                    pass

                            # TODO, also allow (year), example: https://www.discogs.com/release/265497
                            if depositoyear != None:
                                if depositoyear < 1900:
                                    count += 1
                                    errormsgs.append("%8d -- Depósito Legal (impossible year): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                elif depositoyear > currentyear:
                                    count += 1
                                    errormsgs.append("%8d -- Depósito Legal (impossible year): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                elif year < depositoyear:
                                    count += 1
                                    errormsgs.append("%8d -- Depósito Legal (release date earlier): https://www.discogs.com/release/%s" % (count, str(release_id)))
                            else:
                                count += 1
                                errormsgs.append("%8d -- Depósito Legal (year not found): https://www.discogs.com/release/%s" % (count, str(release_id)))
                        pass
                    elif identifier['type'] == 'Barcode':
                        for depositovalre in discogssmells.depositovalres:
                            if depositovalre.match(v.lower()) != None:
                                founddeposito = True
                                count += 1
                                errormsgs.append('%8d -- Depósito Legal (in Barcode): https://www.discogs.com/release/%s' % (count, str(release_id)))
                                break
                    else:
                        if v.startswith("Depósito"):
                            founddeposito = True
                            count += 1
                            errormsgs.append('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        elif v.startswith("D.L."):
                            founddeposito = True
                            count += 1
                            errormsgs.append('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        else:
                            if 'description' in identifier:
                                found = False
                                for d in discogssmells.depositores:
                                    result = d.search(identifier['description'].lower())
                                    if result != None:
                                        found = True
                                        break

                                # sometimes the depósito value itself can be found in the free text field
                                if not found:
                                    for depositovalre in discogssmells.depositovalres:
                                        deposres = depositovalre.match(identifier['description'].lower())
                                        if deposres != None:
                                            found = True
                                            break

                                if found:
                                    founddeposito = True
                                    count += 1
                                    errormsgs.append('%8d -- Depósito Legal (BaOI): https://www.discogs.com/release/%s' % (count, str(release_id)))

        # temporary hack, move to own configuration option
        mould_sid_strict = False
        if config_settings['check_mould_sid']:
            if identifier['type'] == 'Mould SID Code':
                if v.strip() != 'none':
                    # cleanup first for not so heavy formatting booboos
                    mould_tmp = v.strip().lower().replace(' ', '')
                    mould_tmp = mould_tmp.replace('-', '')
                    # some people insist on using ƒ instead of f
                    mould_tmp = mould_tmp.replace('ƒ', 'f')
                    res = discogssmells.mouldsidre.match(mould_tmp)
                    if res == None:
                        count += 1
                        errormsgs.append('%8d -- Mould SID Code (value): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    else:
                        if mould_sid_strict:
                            mould_split = mould_tmp.split('ifpi', 1)[-1]
                            for ch in ['i', 'o', 's', 'q']:
                                if ch in mould_split[-2:]:
                                    count += 1
                                    errormsgs.append('%8d -- Mould SID Code (strict value): https://www.discogs.com/release/%s' % (count, str(release_id)))
                        # rough check to find SID codes for formats other than CD/CD-like
                        if len(formattexts) == 1:
                            for fmt in set(['Vinyl', 'Cassette', 'Shellac', 'File', 'VHS', 'DCC', 'Memory Stick', 'Edison Disc']):
                                if fmt in formattexts:
                                    count += 1
                                    errormsgs.append('%8d -- Mould SID Code (Wrong Format: %s): https://www.discogs.com/release/%s' % (count, fmt, str(release_id)))
                                    break
                        if year != None:
                            if year < 1993:
                                count += 1
                                errormsgs.append('%8d -- SID Code (wrong year): https://www.discogs.com/release/%s' % (count, str(release_id)))

            else:
                if 'description' in identifier:
                    description = identifier['description'].lower()
                    # squash repeated spaces
                    description = re.sub('\s+', ' ', description)
                    description = description.strip()
                    if description in ['source identification code', 'sid', 'sid code', 'sid-code']:
                        count += 1
                        errormsgs.append('%8d -- Unspecified SID Code: https://www.discogs.com/release/%s' % (count, str(release_id)))
                    elif description in discogssmells.mouldsids:
                        count += 1
                        errormsgs.append('%8d -- Mould SID Code: https://www.discogs.com/release/%s' % (count, str(release_id)))

        if config_settings['check_mastering_sid']:
            if identifier['type'] == 'Mastering SID Code':
                if v.strip() != 'none':
                    # cleanup first for not so heavy formatting booboos
                    master_tmp = v.strip().lower().replace(' ', '')
                    master_tmp = master_tmp.replace('-', '')
                    # some people insist on using ƒ instead of f
                    master_tmp = master_tmp.replace('ƒ', 'f')
                    res = discogssmells.masteringsidre.match(master_tmp)
                    if res == None:
                        count += 1
                        errormsgs.append('%8d -- Mastering SID Code (value): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    else:
                        # rough check to find SID codes for formats other than CD/CD-like
                        if len(formattexts) == 1:
                            for fmt in set(['Vinyl', 'Cassette', 'Shellac', 'File', 'VHS', 'DCC', 'Memory Stick', 'Edison Disc']):
                                if fmt in formattexts:
                                    count += 1
                                    errormsgs.append('%8d -- Mastering SID Code (Wrong Format: %s): https://www.discogs.com/release/%s' % (count, fmt, str(release_id)))
                        if year != None:
                            if year < 1993:
                                count += 1
                                errormsgs.append('%8d -- SID Code (wrong year): https://www.discogs.com/release/%s' % (count, str(release_id)))
            else:
                if 'description' in identifier:
                    description = identifier['description'].lower()
                    # squash repeated spaces
                    description = re.sub('\s+', ' ', description)
                    description = description.strip()
                    if description in ['source identification code', 'sid', 'sid code', 'sid-code']:
                        count += 1
                        errormsgs.append('%8d -- Unspecified SID Code: https://www.discogs.com/release/%s' % (count, str(release_id)))
                    elif description in discogssmells.masteringsids:
                        count += 1
                        errormsgs.append('%8d -- Mastering SID Code: https://www.discogs.com/release/%s' % (count, str(release_id)))
                    elif description in ['sid code matrix', 'sid code - matrix', 'sid code (matrix)', 'sid-code, matrix', 'sid-code matrix', 'sid code (matrix ring)', 'sid code, matrix ring', 'sid code: matrix ring']:
                        count += 1
                        errormsgs.append('%8d -- Possible Mastering SID Code: https://www.discogs.com/release/%s' % (count, str(release_id)))
        if config_settings['check_pkd']:
            if 'country' in release:
                if release['country'] == 'India':
                    if 'pkd' in v.lower() or "production date" in v.lower():
                        if year != None:
                            # try a few variants
                            pkdres = re.search("\d{1,2}/((?:19|20)?\d{2})", v)
                            if pkdres != None:
                                pkdyear = int(pkdres.groups()[0])
                                if pkdyear < 100:
                                    # correct the year. This won't work correctly after 2099.
                                    if pkdyear <= currentyear - 2000:
                                        pkdyear += 2000
                                    else:
                                        pkdyear += 1900
                                if pkdyear < 1900:
                                    count += 1
                                    errormsgs.append("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                elif pkdyear > currentyear:
                                    count += 1
                                    errormsgs.append("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                elif year < pkdyear:
                                    count += 1
                                    errormsgs.append("%8d -- Indian PKD (release date earlier): https://www.discogs.com/release/%s" % (count, str(release_id)))
                        else:
                            count += 1
                            errormsgs.append('%8d -- India PKD code (no year): https://www.discogs.com/release/%s' % (count, str(release_id)))
                    else:
                        # now check the description
                        if 'description' in identifier:
                            description = identifier['description'].lower()
                            if 'pkd' in description or "production date" in description:
                                if year != None:
                                    # try a few variants
                                    pkdres = re.search("\d{1,2}/((?:19|20)?\d{2})", attrvalue)
                                    if pkdres != None:
                                        pkdyear = int(pkdres.groups()[0])
                                        if pkdyear < 100:
                                            # correct the year. This won't work correctly after 2099.
                                            if pkdyear <= currentyear - 2000:
                                                pkdyear += 2000
                                            else:
                                                pkdyear += 1900
                                        if pkdyear < 1900:
                                            count += 1
                                            errormsgs.append("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                        elif pkdyear > currentyear:
                                            count += 1
                                            errormsgs.append("%8d -- Indian PKD (impossible year): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                        elif year < pkdyear:
                                            count += 1
                                            errormsgs.append("%8d -- Indian PKD (release date earlier): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                    else:
                                        count += 1
                                        errormsgs.append('%8d -- India PKD code (no year): https://www.discogs.com/release/%s' % (count, str(release_id)))
        # check Czechoslovak manufacturing dates
        if config_settings['check_manufacturing_date_cs']:
            # config hack, needs to be in its own configuration option
            strict_cs = False
            strict_cs = True
            if 'country' in release:
                if release['country'] == 'Czechoslovakia':
                    if 'description' in identifier:
                        description = identifier['description'].lower()
                        if 'date' in description:
                            if year != None:
                                manufacturing_date_res = re.search("(\d{2})\s+\d$", identifier['value'].rstrip())
                                if manufacturing_date_res != None:
                                    manufacturing_year = int(manufacturing_date_res.groups()[0])
                                    if manufacturing_year < 100:
                                        manufacturing_year += 1900
                                        if manufacturing_year > year:
                                            count += 1
                                            errormsgs.append("%8d -- Czechoslovak manufacturing date (release year wrong): https://www.discogs.com/release/%s" % (count, str(release_id)))
                                        # possibly this check makes sense, but not always
                                        elif manufacturing_year < year and strict_cs:
                                            count += 1
                                            errormsgs.append("%8d -- Czechoslovak manufacturing date (release year possibly wrong): https://www.discogs.com/release/%s" % (count, str(release_id)))

    # finally check the notes for some errors
    if 'notes' in release:
        if '카지노' in release['notes']:
            # Korean casino spam that pops up every once in a while
            errormsgs.append('Spam: https://www.discogs.com/release/%s' % str(release_id))
        if 'country' in release:
            if release['country'] == 'Spain':
                if config_settings['check_deposito'] and not founddeposito:
                    # sometimes "deposito legal" can be found in the "notes" section
                    content_lower = release['notes'].lower()
                    for d in discogssmells.depositores:
                        result = d.search(content_lower)
                        if result != None:
                            count += 1
                            found = True
                            errormsgs.append('%8d -- Depósito Legal (Notes): https://www.discogs.com/release/%s' % (count, str(release_id)))
                            break
        if config_settings['check_html']:
            # see https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-
            if '&lt;a href="http://www.discogs.com/release/' in release['notes'].lower():
                count += 1
                errormsgs.append('%8d -- old link (Notes): https://www.discogs.com/release/%s' % (count, str(release_id)))
        if config_settings['check_creative_commons']:
            ccfound = False
            for cc in discogssmells.creativecommons:
                if cc in release['notes']:
                    count += 1
                    errormsgs.append('%8d -- Creative Commons reference (%s): https://www.discogs.com/release/%s' % (count, cc, str(release)))
                    ccfound = True
                    break

                if not ccfound:
                    if 'creative commons' in reales['notes'].lower():
                        count += 1
                        errormsgs.append('%8d -- Creative Commons reference: https://www.discogs.com/release/%s' % (count, str(release)))
                        ccfound = True
                        break

    for e in errormsgs:
        print(e)
        if config_settings['use_notify_send']:
            p = subprocess.Popen(['notify-send', "-t", "3000", "Error", e], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stanout, stanerr) = p.communicate()
    sys.stdout.flush()
    return count

def main(argv):
    parser = argparse.ArgumentParser()

    # the following options are provided on the commandline
    parser.add_argument("-c", "--config", action="store", dest="cfg", help="path to configuration file", metavar="FILE")
    parser.add_argument("-s", "--startvalue", action="store", dest="startvalue", help="start value for releases", metavar="STARTVALUE")
    parser.add_argument("-l", "--latest", action="store", dest="latest_value", help="value for latest release", metavar="LATEST")
    args = parser.parse_args()

    # some checks for the configuration file
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

    startvalue = None
    # check for a startvalue
    if args.startvalue != None:
        try:
            startvalue = int(args.startvalue)
        except:
            parser.error("start value is not a valid integer, exciting")

    latest_release = None
    # check for a startvalue
    if args.latest_value != None:
        try:
            latest_release = int(args.latest_value)
        except:
            parser.error("latest value is not a valid integer, exciting")

    # process the configuration file and store settings
    config_settings = {}

    for section in config.sections():
        if section == 'cleanup':
            # store settings for depósito legal checks
            try:
                if config.get(section, 'deposito') == 'yes':
                    config_settings['check_deposito'] = True
                else:
                    config_settings['check_deposito'] = False
            except Exception:
                config_settings['check_deposito'] = True

            # store settings for rights society checks
            try:
                if config.get(section, 'rights_society') == 'yes':
                    config_settings['check_rights_society'] = True
                else:
                    config_settings['check_rights_society'] = False
            except Exception:
                config_settings['check_rights_society'] = True

            # store settings for label code checks
            try:
                if config.get(section, 'label_code') == 'yes':
                    config_settings['check_label_code'] = True
                else:
                    config_settings['check_label_code'] = False
            except Exception:
                config_settings['check_label_code'] = True

            # store settings for label name checks
            try:
                if config.get(section, 'label_name') == 'yes':
                    config_settings['check_label_name'] = True
                else:
                    config_settings['check_label_name'] = False
            except Exception:
                config_settings['check_label_name'] = True

            # store settings for ISRC checks
            try:
                if config.get(section, 'isrc') == 'yes':
                    config_settings['check_isrc'] = True
                else:
                    config_settings['check_isrc'] = False
            except Exception:
                config_settings['check_isrc'] = True

            # store settings for ASIN checks
            try:
                if config.get(section, 'asin') == 'yes':
                    config_settings['check_asin'] = True
                else:
                    config_settings['check_asin'] = False
            except Exception:
                config_settings['check_asin'] = True

            # store settings for mastering SID checks
            try:
                if config.get(section, 'mastering_sid') == 'yes':
                    config_settings['check_mastering_sid'] = True
                else:
                    config_settings['check_mastering_sid'] = False
            except Exception:
                config_settings['check_mastering_sid'] = True

            # store settings for mould SID checks
            try:
                if config.get(section, 'mould_sid') == 'yes':
                    config_settings['check_mould_sid'] = True
                else:
                    config_settings['check_mould_sid'] = False
            except Exception:
                config_settings['check_mould_sid'] = True

            # store settings for SPARS Code checks
            try:
                if config.get(section, 'spars') == 'yes':
                    config_settings['check_spars_code'] = True
                else:
                    config_settings['check_spars_code'] = False
            except Exception:
                config_settings['check_spars_code'] = True

            # store settings for Indian PKD checks
            try:
                if config.get(section, 'pkd') == 'yes':
                    config_settings['check_pkd'] = True
                else:
                    config_settings['check_pkd'] = False
            except Exception:
                config_settings['check_pkd'] = True

            # check for Czechoslovak manufacturing dates
            try:
                if config.get(section, 'manufacturing_date_cs') == 'yes':
                    config_settings['check_manufacturing_date_cs'] = True
                else:
                    config_settings['check_manufacturing_date_cs'] = False
            except Exception:
                config_settings['check_manufacturing_date_cs'] = True

            # check for Czechoslovak and Czech spelling (0x115 used instead of 0x11B)
            try:
                if config.get(section, 'spelling_cs') == 'yes':
                    config_settings['check_spelling_cs'] = True
                else:
                    config_settings['check_spelling_cs'] = False
            except Exception:
                config_settings['check_spelling_cs'] = True

            # store settings for tracklisting checks, default True
            try:
                if config.get(section, 'tracklisting') == 'yes':
                    config_settings['check_tracklisting'] = True
                else:
                    config_settings['check_tracklisting'] = False
            except Exception:
                config_settings['check_tracklisting'] = True

            # store settings for credits list checks
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

            # store settings for URLs in Notes checks
            try:
                if config.get(section, 'html') == 'yes':
                    config_settings['check_html'] = True
                else:
                    config_settings['check_html'] = False
            except Exception:
                config_settings['check_html'] = True


            # month is 00 check: default is False
            try:
                if config.get(section, 'month') == 'yes':
                    config_settings['check_month'] = True
                else:
                    config_settings['check_month'] = False
            except Exception:
                config_settings['check_month'] = False

            # year is wrong check: default is False
            try:
                if config.get(section, 'year') == 'yes':
                    config_settings['check_year'] = True
                else:
                    config_settings['check_year'] = False
            except Exception:
                config_settings['check_year'] = False

            # reporting all: default is False
            try:
                if config.get(section, 'reportall') == 'yes':
                    config_settings['reportall'] = True
                else:
                    config_settings['reportall'] = False
            except Exception:
                config_settings['reportall'] = False

            # debug: default is False
            try:
                if config.get(section, 'debug') == 'yes':
                    config_settings['debug'] = True
                else:
                    config_settings['debug'] = False
            except Exception:
                config_settings['debug'] = False

            # report creative commons references: default is False
            try:
                if config.get(section, 'creative_commons') == 'yes':
                    config_settings['check_creative_commons'] = True
                else:
                    config_settings['check_creative_commons'] = False
            except Exception:
                config_settings['check_creative_commons'] = False

        elif section == 'api':
            # data directory to store JSON files
            try:
                storedir = config.get(section, 'storedir')
                if not os.path.exists(os.path.normpath(storedir)):
                    config_settings['storedir'] = None
                else:
                    # test if the directory is writable
                    testfile = tempfile.mkstemp(dir=storedir)
                    os.fdopen(testfile[0]).close()
                    os.unlink(testfile[1])
                    config_settings['storedir'] = storedir
            except Exception:
                config_settings['storedir'] = None
                break
            try:
                token = config.get(section, 'token')
                config_settings['token'] = token
            except Exception:
                config_settings['token'] = None
            try:
                username = config.get(section, 'username')
                config_settings['username'] = username
            except Exception:
                config_settings['username'] = None

            # skipdownloaded: default is False
            config_settings['skipdownloaded'] = False
            try:
                if config.get(section, 'skipdownloaded') == 'yes':
                    config_settings['skipdownloaded'] = True
            except Exception:
                pass

            # skip404: default is True
            config_settings['skip404'] = True
            try:
                if config.get(section, 'skip404') == 'yes':
                    config_settings['skip404'] = True
                else:
                    config_settings['skip404'] = False
            except Exception:
                pass

            # record404: default is True
            config_settings['record404'] = True
            try:
                if config.get(section, 'record404') == 'yes':
                    config_settings['record404'] = True
                else:
                    config_settings['record404'] = False
            except Exception:
                pass

            # specify location of 404 file
            try:
                release404 = os.path.normpath(config.get(section, '404file'))
                config_settings['404file'] = release404
            except:
                pass

            # specify whether or not notify-send (Linux desktops
            # should be used or not. Not recommended.
            config_settings['use_notify_send'] = True
            try:
                if config.get(section, 'notify') == 'yes':
                    config_settings['use_notify_send'] = True
                else:
                    config_settings['use_notify_send'] = False
            except Exception:
                pass

    if config_settings['use_notify_send']:
        try:
            p = subprocess.Popen(['notify-send', "-t", "3000", "Test for notify-send"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stanout, stanerr) = p.communicate()
        except Exception:
            config_settings['use_notify_send'] = False

    configfile.close()
    if config_settings['storedir'] == None:
        print("Data store directory non-existent or not writable, exiting.", file=sys.stderr)
        sys.exit(1)
    if config_settings['token'] == None:
        print("Token not specified, exiting.", file=sys.stderr)
        sys.exit(1)
    if config_settings['username'] == None:
        print("Discogs user name not specified, exiting.", file=sys.stderr)
        sys.exit(1)

    # a list of accepted roles. This is an external file, generated with extractcredits.py
    # from the 'helper-scripts' directory.
    credits = set()
    if 'check_credits' in config_settings:
        if config_settings['check_credits']:
            creditsfile = open(config_settings['creditsfile'], 'r')
            credits = set(map(lambda x: x.strip(), creditsfile.readlines()))
            creditsfile.close()

    # a file with release numbers that give a 404 error
    # This needs more work
    if config_settings['skip404']:
        if '404file' in config_settings:
            if not os.path.isabs(config_settings['404file']):
                release404filename = os.path.join(config_settings['storedir'], config_settings['404file'])
                if not os.path.exists(release404filename):
                    release404file = open(release404filename, 'w')
                    release404file.close()
            else:
                release404filename = config_settings['404file']
        else:
            # simply create the file
            pass

    # use a (somewhat) exponential backoff in case too many requests have been made
    ratelimitbackoff = 5

    # set the User Agent and Authorization header for each user request
    useragentstring = "DiscogsCleanupForUser%s/0.1" % config_settings['username']
    headers = {'user-agent': useragentstring, 'Authorization': 'Discogs token=%s' % config_settings['token']}

    if latest_release is None:
        latest_release = get_latest_release(headers)
        if latest_release == None:
            print("Something went wrong, try again later", file=sys.stderr)
            sys.exit(1)

    # if no start value has been provided start with the latest from the
    # Discogs website.
    if startvalue == None:
        startvalue = latest_release

    # populate a set with all the 404s that were found.
    skip404s = set()
    count = 0
    if config_settings['skip404']:
        release404file = open(release404filename, 'r')
        for l in release404file:
            # needs to be made more robust
            skip404s.add(int(l.strip()))
        release404file.close()
        # now open again for writing, so new 404 errors can be
        # stored.
        release404file = open(release404filename, 'a')

    # This is just something very silly: if you have an iBuddy device and have the
    # corresponding Python module installed it will respond to things it finds
    # (currently only favourite artists).
    #
    # https://github.com/armijnhemel/py3buddy
    #
    # Not recommended.
    ibuddy_enabled = False
    try:
        import py3buddy
        ibuddy_enabled = True
    except:
        pass

    ibuddy = None
    if ibuddy_enabled:
        ibuddy_config = {}
        ibuddy = py3buddy.iBuddy(ibuddy_config)
        if ibuddy.dev == None:
            ibuddy = None
            ibuddy_enabled = False

    # example:
    #favourites = set(['Bob Dylan', 'Iron Maiden', 'The Beatles'])
    favourites = set()

    newsleep = 600

    # now start a big loop
    # https://www.discogs.com/developers/#page:authentication
    while(True):
        for releasenr in range(startvalue, latest_release):
            if startvalue == latest_release:
                break
            targetfilename = os.path.join(storedir, "%d" % (releasenr//1000000), "%d.json" % releasenr)
            os.makedirs(os.path.join(storedir, "%d" % (releasenr//1000000)), exist_ok=True)
            if config_settings['skip404']:
                if releasenr in skip404s:
                    continue
            if config_settings['skipdownloaded']:
                if os.path.exists(targetfilename):
                    if os.stat(targetfilename).st_size != 0:
                        responsejsonfile = open(targetfilename, 'r')
                        responsejson = json.loads(responsejsonfile.read())
                        responsejsonfile.close()
                        count = processrelease(responsejson, config_settings, count, credits, ibuddy, favourites)
                        continue
            print("downloading: %d" % releasenr, file=sys.stderr)
            r = requests.get('https://api.discogs.com/releases/%d' % releasenr, headers=headers)

            # now first check the headers to see if it is OK to do more requests
            if r.status_code != 200:
                if r.status_code == 404:
                    print("%d" % releasenr, file=release404file)
                    release404file.flush()
                if r.status_code == 429:
                    if 'Retry-After' in r.headers:
                        try:
                            retryafter = int(r.headers['Retry-After'])
                            print("Rate limiting, sleeping for %d seconds" % retryafter, file=sys.stderr)
                            time.sleep(retryafter)
                            sys.stderr.flush()
                        except:
                            print("Rate limiting, sleeping for %d seconds" % 60, file=sys.stderr)
                            time.sleep(60)
                            sys.stderr.flush()
                    else:
                        print("Rate limiting, sleeping for %d seconds" % 60, file=sys.stderr)
                        time.sleep(60)
                        sys.stderr.flush()
                # TODO: the current release will not have been downloaded and processed
                continue

            # in case there is no 429 response check the headers
            if 'X-Discogs-Ratelimit-Remaining' in r.headers:
                ratelimit = int(r.headers['X-Discogs-Ratelimit-Remaining'])
            if ratelimit == 0:
                # no more requests are allowed, so sleep for some time, max 60 seconds
                time.sleep(ratelimitbackoff)
                print("Rate limiting, sleeping for %d seconds" % ratelimitbackoff, file=sys.stderr)
                sys.stderr.flush()
                if ratelimitbackoff < 60:
                    ratelimitbackoff = min(60, ratelimitbackoff * 2)
            else:
                ratelimitbackoff = 5

            # now process the response. This should be JSON, so decode it, and also write
            # the JSON data to a separate file for offline processing (if necessary).
            try:
                responsejson = r.json()
                jsonreleasefile = open(targetfilename, 'w')
                jsonreleasefile.write(r.text)
                jsonreleasefile.close()
            except:
                # response doesn't contain JSON, so something is wrong.
                # sleep a bit then continue
                time.sleep(2)
                continue
            # now process the JSON content
            count = processrelease(responsejson, config_settings, count, credits, ibuddy, favourites)
            # be gentle for Discogs and sleep
            time.sleep(0.2)
            sys.stderr.flush()

        # now set startvalue to latest_release
        startvalue = latest_release

        # and find the newest release again
        print("Grabbing new data", file=sys.stderr)
        latest_release = get_latest_release(headers)
        if latest_release == None:
            print("Something went wrong, try again later", file=sys.stderr)
            sys.exit(1)
        if latest_release < startvalue:
            pass
        print("Latest = %d" % latest_release, file=sys.stderr)
        print("Sleeping for %d seconds" % newsleep, file=sys.stderr)
        sys.stderr.flush()

        # sleep for ten minutes to make sure some new things have been added to Discogs
        time.sleep(newsleep)
    release404file.close()

if __name__ == "__main__":
    main(sys.argv)
