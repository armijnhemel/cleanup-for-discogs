#!/usr/bin/env python3

# Tool to discover 'smells' in the Discogs data dump. It prints a list of URLs
# of releases that need to be fixed.
#
# The results that are printed by this script are
# by no means complete or accurate
#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright 2017-2024 - Armijn Hemel

import configparser
import datetime
import gzip
import pathlib
import re
import sys

from dataclasses import dataclass

import defusedxml.ElementTree as et

import click
import discogssmells

ISRC_TRANSLATE = str.maketrans({'-': None, ' ': None, '.': None,
                                ':': None, '–': None,})

# a list of possible label code false positives. These are
# used when checking the catalog numbers.
LABEL_CODE_FALSE_POSITIVES = set([654, 1005, 1060, 2495, 5320, 11358, 20234, 20561, 22804, 23541,
                                  29480, 38653, 39161, 54361, 63510, 66210, 97031, 113617, 127100,
                                  163947, 185266, 199380, 226480, 237745, 238695, 251227, 253128,
                                  487381, 498544, 510628, 593249, 620121, 645109, 656580, 810881,
                                  1210375, 1446781, 1674048])

RIGHTS_SOCIETY_DELIMITERS = ['/', '|', '\\', '-', '—', '•', '·', ',', ':', ' ', '&', '+']

# a quick and dirty translation table to see if rights society values
# are correct. This is just for the first big sweep.
RIGHTS_SOCIETY_TRANSLATE_QND = str.maketrans({'.': None, ' ': None, '•': None,
                                              '[': None, ']': None, '(': None,
                                              ')': None})

SID_INVALID_FORMATS = set(['Vinyl', 'Cassette', 'Shellac', 'File',
                           'VHS', 'DCC', 'Memory Stick', 'Edison Disc'])

# SID descriptions (either Mastering or Mould)
SID_DESCRIPTIONS = ['source identification code', 'sid', 'sid code', 'sid-code']

SPARS_TRANSLATE = str.maketrans({'.': None, ' ': None, '•': None, '·': None,
                                 '∙': None, '᛫': None, '[': None, ']': None,
                                 '-': None, '|': None, '︱': None, '/': None,
                                 '\\': None})

# Translation table for SID codes as some people
# insist on using ƒ/⨍ instead of f or ρ/ƥ instead of p
SID_TRANSLATE = str.maketrans({' ': None, '-': None,
                              '⨍': 'f', 'ƒ': 'f',
                              'ρ': 'p', 'ƥ': 'p'})

TRACKLIST_CHECK_FORMATS = ['Vinyl', 'Cassette', 'Shellac', '8-Track Cartridge']

# grab the current year. Make sure to set the clock of your machine
# to the correct date or use NTP!
CURRENT_YEAR = datetime.datetime.now(datetime.UTC).year

pkd_re = re.compile(r"\d{1,2}/((?:19|20)?\d{2})")

@dataclass
class CleanupConfig:
    '''Default cleanup configuration'''
    artist: bool = False
    asin: bool = True
    cd_plus_g: bool = True
    creative_commons: bool = False
    credits: bool = False
    czechoslovak_dates: bool = True
    czechoslovak_dates_strict: bool = False
    czechoslovak_spelling: bool = True
    debug: bool = False
    deposito_legal: bool = True
    greek_license: bool = True
    indian_pkd: bool = True
    isrc: bool = True
    label_code: bool = True
    label_name: bool = True
    labels: bool = True
    mastering_sid: bool = True
    matrix: bool = True
    month_valid: bool = False
    mould_sid: bool = True
    mould_sid_strict: bool = False
    pressing_plants: bool = True
    report_all: bool = False
    rights_society: bool = True
    spars: bool = True
    tracklisting: bool = True
    url_in_html: bool = True
    year_valid: bool = False


def print_error(counter, reason, release_id):
    '''Helper method for printing errors'''
    print(f'{counter: 8} -- {reason}: https://www.discogs.com/release/{release_id}')
    sys.stdout.flush()

def check_role(role):
    '''Helper method for checking roles'''
    pass

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

def check_rights_society(value):
    '''Helper method for checking rights societies'''
    errors = []
    value = value.translate(RIGHTS_SOCIETY_TRANSLATE_QND)
    if value in discogssmells.rights_societies_wrong:
        errors.append(f"possible wrong value: {value}")

    if value in discogssmells.rights_societies_wrong_char:
        errors.append(f"wrong character set: {value}")

    return errors

@click.command(short_help='process Discogs datadump files and print errors found')
@click.option('--config-file', '-c', 'cfg', required=True, help='configuration file',
              type=click.File('r'))
@click.option('--datadump', '-d', 'datadump', required=True, help='discogs data dump file',
              type=click.Path(exists=True))
@click.option('--release', '-r', 'requested_release', help='release number to scan', type=int)
def main(cfg, datadump, requested_release):
    config = configparser.ConfigParser()

    try:
        config.read_file(cfg)
    except Exception:
        print("Cannot read configuration file", file=sys.stderr)
        sys.exit(1)

    # process the configuration file and store settings.
    # Most of the defaults (but not all!) are set to 'True'
    config_settings = CleanupConfig()

    # store settings for depósito legal checks
    try:
        config_settings.deposito_legal = config.getboolean('cleanup', 'deposito')
    except:
        pass

    # store settings for rights society checks
    try:
        config_settings.rights_society = config.getboolean('cleanup', 'rights_society')
    except:
        pass

    # store settings for label code checks
    try:
        config_settings.label_code = config.getboolean('cleanup', 'label_code')
    except:
        pass

    # store settings for label name checks
    try:
        config_settings.label_name = config.getboolean('cleanup', 'label_name')
    except:
        pass

    # store settings for ISRC checks
    try:
        config_settings.isrc = config.getboolean('cleanup', 'isrc')
    except:
        pass

    # store settings for ASIN checks
    try:
        config_settings.asin = config.getboolean('cleanup', 'asin')
    except:
        pass

    # store settings for mastering SID checks
    try:
        config_settings.mastering_sid = config.getboolean('cleanup', 'mastering_sid')
    except:
        pass

    # store settings for mould SID checks
    try:
        config_settings.mould_sid = config.getboolean('cleanup', 'mould_sid')
    except:
        pass

    # store settings for mould SID strict checks
    try:
        config_settings.mould_sid_strict = config.getboolean('cleanup', 'mould_sid_strict')
    except:
        pass

    # store settings for SPARS Code checks
    try:
        config_settings.spars = config.getboolean('cleanup', 'spars')
    except:
        pass

    # store settings for Indian PKD checks
    try:
        config_settings.indian_pkd = config.getboolean('cleanup', 'pkd')
    except:
        pass

    # store settings for Greek license number checks
    try:
        config_settings.greek_license = config.getboolean('cleanup', 'greek_license_number')
    except:
        pass

    # store settings for CD+G checks
    try:
        config_settings.cd_plus_g = config.getboolean('cleanup', 'cdg')
    except:
        pass

    # store settings for Matrix checks
    try:
        config_settings.matrix = config.getboolean('cleanup', 'matrix')
    except:
        pass

    # store settings for label checks
    try:
        config_settings.labels = config.getboolean('cleanup', 'labels')
    except:
        pass

    # store settings for manufacturing plant checks
    try:
        config_settings.pressing_plants = config.getboolean('cleanup', 'plants')
    except:
        pass

    # check for Czechoslovak manufacturing dates
    try:
        config_settings.czechoslovak_dates = config.getboolean('cleanup', 'manufacturing_date_cs')
    except:
        pass

    # check for strict Czechoslovak manufacturing dates
    try:
        config_settings.czechoslovak_dates_strict = config.getboolean('cleanup', 'manufacturing_date_cs_strict')
    except:
        pass

    # check for Czechoslovak and Czech spelling (0x115 used instead of 0x11B)
    try:
        config_settings.czechoslovak_spelling = config.getboolean('cleanup', 'spelling_cs')
    except:
        pass

    # store settings for tracklisting checks, default True
    try:
        config_settings.tracklisting = config.getboolean('cleanup', 'tracklisting')
    except:
        pass

    # store settings for artists, default False
    try:
        config_settings.artist = config.getboolean('cleanup', 'artist')
    except:
        pass

    # store known valid credits
    credit_roles = set()

    # store settings for credits list checks, implies artist checks
    # This only makes sense if there is a valid credits file
    try:
        if config.get('cleanup', 'credits') == 'yes':
            creditsfile = pathlib.Path(config.get('cleanup', 'creditsfile'))
            if creditsfile.exists():
                config_settings.credits = True
                with open(creditsfile, 'r') as open_file:
                    credit_roles = set(map(lambda x: x.strip(), open_file.readlines()))
                if credit_roles != set():
                    config_settings.artist = True
                else:
                    config_settings.credits = False
    except:
        pass

    # store settings for URLs in Notes checks
    try:
        config_settings.url_in_html = config.getboolean('cleanup', 'html')
    except:
        pass

    # month is 00 check: default is False
    try:
        config_settings.month_valid = config.getboolean('cleanup', 'month')
    except:
        pass

    # year is wrong check: default is False
    try:
        config_settings.year_valid = config.getboolean('cleanup', 'year')
    except:
        pass

    # reporting all: default is False
    try:
        config_settings.report_all = config.getboolean('cleanup', 'reportall')
    except:
        pass

    # debug: default is False
    try:
        config_settings.debug = config.getboolean('cleanup', 'debug')
    except:
        pass

    # report creative commons references: default is False
    try:
        config_settings.creative_commons = config.getboolean('cleanup', 'creative_commons')
    except:
        pass

    try:
        with gzip.open(datadump, "rb") as dumpfile:
            counter = 1
            prev_counter = 1
            last_release_checked = 0
            ignore_status = ['Deleted', 'Draft', 'Rejected']
            for event, element in et.iterparse(dumpfile):
                if element.tag == 'release':
                    # store the release id
                    release_id = int(element.get('id'))

                    # skip the release if -r was passed on the command line
                    if requested_release is not None:
                        if requested_release > release_id:
                            # reduce memory usage
                            element.clear()
                            continue
                        if requested_release < release_id:
                            print(f'Release {requested_release} cannot be found in data set!',
                                  file=sys.stderr)
                            sys.exit(1)

                    # first see if a release is worth looking at
                    status = element.get('status')
                    if status in ignore_status:
                        continue

                    # then store various things about the release
                    country = ""
                    deposito_found = False
                    deposito_found_in_notes = False
                    year = None
                    formats = set()
                    num_formats = 0
                    is_cd = False

                    # data structures specific for detecting reuse of
                    # ISRC codes and descriptions.
                    isrcs_seen = set()
                    isrc_descriptions_seen = set()

                    # genres, currently not used in a check
                    genres = set()

                    # first store the country to make sure it is always available
                    # for for various country checks (like Czech misspellings)
                    for child in element:
                        if child.tag == 'country':
                            country = child.text
                            break

                    # and process the different elements
                    for child in element:
                        if config_settings.report_all:
                            if release_id == last_release_checked:
                                break

                        if country in ['Czechoslovakia', 'Czech Republic']:
                            if config_settings.czechoslovak_spelling:
                                # People use 0x115 instead of 0x11B, which look very similar
                                # but 0x115 is not valid in the Czech alphabet. Check for all
                                # data except the YouTube playlist.
                                # https://www.discogs.com/group/thread/757556
                                if child.tag != 'videos':
                                    czech_error_found = False
                                    for iter_child in child.iter():
                                        for i in ['description', 'value']:
                                            free_text = iter_child.get(i, '').lower()
                                            if chr(0x115) in free_text:
                                                print_error(counter, 'Czech character (0x115)', release_id)
                                                counter += 1
                                                czech_error_found = True
                                                break
                                        if czech_error_found:
                                            break

                        if child.tag == 'artists' or child.tag == 'extraartists':
                            if config_settings.artist:
                                for artist_elem in child:
                                    # set to "no artist" as a place holder
                                    artist_id = 0
                                    artist_name = ''
                                    for artist in artist_elem:
                                        if artist.tag == 'id':
                                            artist_id = int(artist.text)
                                            # TODO: check for genres, as No Artist is
                                            # often confused with Unknown Artist
                                            #if artist_id == 118760:
                                            #    if genres:
                                            #        print_error(counter, f'https://www.discogs.com/artist/{artist_id}' release_id)
                                            #        counter += 1
                                        elif artist.tag == 'name':
                                            artist_name = artist.text
                                        elif artist.tag == 'role':
                                            '''
                                            if artist_id == 0:
                                                wrong_role_for_noartist = True
                                                for r in ['Other', 'Artwork By', 'Executive Producer', 'Photography', 'Written By']:
                                                    if r in artist.text.strip():
                                                        wrong_role_for_noartist = False
                                                        break
                                                if wrong_role_for_noartist:
                                                    pass
                                                    #print(self.contentbuffer.strip(), " -- https://www.discogs.com/release/%s" % str(self.release))
                                            '''
                                            if config_settings.credits:
                                                role_data = artist.text
                                                if role_data is None:
                                                    continue
                                                role_data = role_data.strip()
                                                if role_data != '':
                                                    if '[' not in role_data:
                                                        roles = map(lambda x: x.strip(), role_data.split(','))
                                                        for role in roles:
                                                            if role == '':
                                                                continue
                                                            if role not in credit_roles:
                                                                print_error(counter, f'Role \'{role}\' invalid', release_id)
                                                                counter += 1
                                                    else:
                                                        # sometimes there is an additional description
                                                        # in the role in between [ and ]. TODO: rework this
                                                        rolesplit = role_data.split('[')
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
                                                                    if role not in credit_roles:
                                                                        print_error(counter, f'Role \'{role}\' invalid', release_id)
                                                                        counter += 1
                                    if artist_id == 0:
                                        print_error(counter, f'Artist \'{artist_name}\' not in database', release_id)
                                        counter += 1
                        elif child.tag == 'companies':
                            if year is not None:
                                for companies in child:
                                    for company in companies:
                                        if company.tag == 'id':
                                            company_nr = int(company.text)
                                            if config_settings.labels:
                                                # check for:
                                                # https://www.discogs.com/label/205-Fontana
                                                # https://www.discogs.com/label/7704-Philips
                                                if company_nr == 205:
                                                    if year < 1957:
                                                        print_error(counter, f'Label (wrong year {year})', release_id)
                                                        counter += 1
                                                elif company_nr == 7704:
                                                    if year < 1950:
                                                        print_error(counter, f'Label (wrong year {year})', release_id)
                                                        counter += 1
                                            if config_settings.pressing_plants:
                                                '''
                                                ## https://www.discogs.com/label/34825-Sony-DADC
                                                if company_nr == 34825:
                                                    if year < 2000:
                                                        print_error(counter, f'Pressing Plant Sony DADC (wrong year {year})', release_id)
                                                        counter += 1
                                                '''

                                                for pl in discogssmells.plants:
                                                    if company_nr == pl[0]:
                                                        if year < pl[1]:
                                                            print_error(counter, f'Pressing Plant {pl[2]} (possibly wrong year {year})', release_id)
                                                            counter += 1
                                                            break

                                                for pl in discogssmells.plants_compact_disc:
                                                    if company_nr == pl[0]:
                                                        if 'CD' in formats:
                                                            if year < pl[1]:
                                                                print_error(counter, f'Pressing Plant {pl[2]} (possibly wrong year {year})', release_id)
                                                                counter += 1
                                                                break

                        elif child.tag == 'formats':
                            for release_format in child:
                                current_format = None

                                # first check the attributes
                                for (key, value) in release_format.items():
                                    if key == 'name':
                                        if value == 'CD':
                                            is_cd = True
                                        formats.add(value)
                                        current_format = value
                                        '''
                                        # https://en.wikipedia.org/wiki/Phonograph_record#Microgroove_and_vinyl_era
                                        if current_format == 'Vinyl' and year is not None:
                                            if year < 1948:
                                                print(counter, f'Impossible year '{year}' for vinyl', release_id)
                                                counter += 1
                                        '''
                                    elif key == 'qty':
                                        if num_formats == 0:
                                            num_formats = max(num_formats, int(value))
                                        else:
                                            num_formats += int(value)
                                    elif key == 'text':
                                        if value != '':
                                            value_lower = value.lower().strip()
                                            if config_settings.spars:
                                                tmp_spars = value_lower
                                                tmp_spars = tmp_spars.translate(SPARS_TRANSLATE)
                                                if tmp_spars in discogssmells.validsparscodes:
                                                    print_error(counter, f"Possible SPARS Code ({value}, in Format)", release_id)
                                                    counter += 1
                                            if config_settings.label_code:
                                                if value_lower.startswith('lc'):
                                                    if discogssmells.labelcodere.match(value_lower) is not None:
                                                        print_error(counter, f"Possible Label Code ({value}, in Format)", release_id)
                                                        counter += 1
                                            if config_settings.cd_plus_g:
                                                if value_lower == 'cd+g':
                                                    print_error(counter, 'CD+G (in Format)', release_id)
                                                    counter += 1
                                            if value_lower == 'DMM':
                                                if current_format != 'Vinyl':
                                                    print_error(f'DMM ({current_format}, in Format)', release_id)
                                                    counter += 1

                                # then process any children
                                for ch in release_format:
                                    if ch.tag == 'descriptions':
                                        for description in ch:
                                            if 'Styrene' in description.text:
                                                pass

                        elif child.tag == 'genres':
                            for genre in child:
                                genres.add(genre.text)
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

                                # ASIN
                                if config_settings.asin:
                                    if identifier_type == 'ASIN':
                                        value = identifier.get('value').strip()
                                        # temporary hack, move to own configuration option
                                        asin_strinct = False
                                        if not asin_strinct:
                                            tmpasin = value.replace('-', '')
                                        else:
                                            tmpasin = value
                                        if not len(tmpasin.split(':')[-1].strip()) == 10:
                                            print_error(counter, 'ASIN (wrong length)', release_id)
                                            counter += 1
                                    else:
                                        description = identifier.get('description', '').strip()
                                        if description.startswith('asin'):
                                            print_error(counter, f'ASIN (in {identifier})', release_id)
                                            counter += 1

                                # creative commons, check value and description
                                if config_settings.creative_commons:
                                    description = identifier.get('description', '').strip().lower()
                                    value = identifier.get('value', '').strip().lower()
                                    if 'creative commons' in description:
                                        print_error(counter, 'Creative Commons reference', release_id)
                                        counter += 1
                                    if 'creative commons' in value:
                                        print_error(counter, 'Creative Commons reference', release_id)
                                        counter += 1

                                if country == 'Czechoslovakia' and year is not None:
                                    if config_settings.czechoslovak_dates:
                                        description = identifier.get('description', '').strip().lower()
                                        value = identifier.get('value', '').strip().lower()
                                        if 'date' in description:
                                            manufacturing_date_res = re.search(r"(\d{2})\s+\d$", value)
                                            if manufacturing_date_res is not None:
                                                manufacturing_year = int(manufacturing_date_res.groups()[0])
                                                if manufacturing_year < 100:
                                                    manufacturing_year += 1900
                                                    if manufacturing_year > year:
                                                        print_error(counter, 'Czechoslovak manufacturing date (release year wrong)', release_id)
                                                        counter += 1
                                                    # possibly this check makes sense, but not always
                                                    elif manufacturing_year < year and config_settings.czechoslovak_dates_strict:
                                                        print_error(counter, 'Czechoslovak manufacturing date (release year possibly wrong)', release_id)
                                                        counter += 1

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
                                                            if deposito_year <= CURRENT_YEAR - 2000:
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
                                                    elif deposito_year > CURRENT_YEAR:
                                                        print_error(counter, f"Depósito Legal (impossible year: {deposito_year})", release_id)
                                                        counter += 1
                                                    elif year < deposito_year:
                                                        print_error(counter, "Depósito Legal (release date earlier)", release_id)
                                                        counter += 1
                                                else:
                                                    print_error(counter, "Depósito Legal (year not found)", release_id)
                                                    counter += 1
                                        else:
                                            value = identifier.get('value').strip()
                                            value_lower = value.lower()
                                            description = identifier.get('description', '').strip()
                                            description_lower = description.lower()

                                            if not deposito_found:
                                                for depositovalre in discogssmells.depositovalres:
                                                    if depositovalre.match(value_lower) is not None:
                                                        print_error(counter, f"Depósito Legal (in {identifier_type})", release_id)
                                                        counter += 1
                                                        deposito_found = True
                                                        break

                                            # check for a DL hint in the description field
                                            if description != '':
                                                if not deposito_found:
                                                    for d in discogssmells.depositores:
                                                        result = d.search(description_lower)
                                                        if result is not None:
                                                            print_error(counter, f"Depósito Legal (in {identifier_type} (description))", release_id)
                                                            counter += 1
                                                            deposito_found = True
                                                            break
                                                    if not deposito_found and config_settings.debug:
                                                        # print descriptions for debugging. Careful.
                                                        print(f'Depósito Legal debug: {release_id}, {description}')

                                                # sometimes the depósito value itself can be
                                                # found in the free text field
                                                if not deposito_found:
                                                    for depositovalre in discogssmells.depositovalres:
                                                        deposres = depositovalre.match(description_lower)
                                                        if deposres is not None:
                                                            print_error(counter, f"Depósito Legal (in {identifier_type} (description))", release_id)
                                                            counter += 1
                                                            deposito_found = True
                                                            break

                                # Greek license numbers
                                if country == 'Greece':
                                    if config_settings.greek_license:
                                        description = identifier.get('description', '').strip().lower()
                                        value = identifier.get('value', '').strip()
                                        if "license" in description.strip() and year is not None:
                                            for sep in ['/', ' ', '-', ')', '\'', '.']:
                                                try:
                                                    license_year = int(value.rsplit(sep, 1)[1])
                                                    if license_year < 100:
                                                        license_year += 1900
                                                    if license_year > year:
                                                        print_error(counter, 'Greek license year wrong', release_id)
                                                        counter += 1
                                                    break
                                                except:
                                                    pass

                                # India PKD
                                if country == 'India':
                                    if config_settings.indian_pkd:
                                        value = identifier.get('value', '').lower()
                                        if 'pkd' in value or "production date" in value:
                                            if year is not None:
                                                # try a few variants
                                                pkdres = pkd_re.search(value)
                                                if pkdres is not None:
                                                    pkdyear = int(pkdres.groups()[0])
                                                    if pkdyear < 100:
                                                        # correct the year. This won't work correctly after 2099.
                                                        if pkdyear <= CURRENT_YEAR - 2000:
                                                            pkdyear += 2000
                                                        else:
                                                            pkdyear += 1900
                                                    if pkdyear < 1900 or pkdyear > CURRENT_YEAR:
                                                        print_error(counter, 'Indian PKD (impossible year)', release_id)
                                                        counter += 1
                                                    elif year < pkdyear:
                                                        print_error(counter, 'Indian PKD (release date earlier)', release_id)
                                                        counter += 1
                                            else:
                                                print_error(counter, 'India PKD code (no year)', release_id)
                                                counter += 1

                                # ISRC
                                if config_settings.isrc:
                                    description = identifier.get('description', '').strip()
                                    description_lower = description.lower()
                                    if identifier_type == 'ISRC':
                                        # Check the length of ISRC fields. According to the
                                        # specifications these should be 12 in length. Some
                                        # ISRC identifiers that have been recorded in the
                                        # database cover a range of tracks. These will be
                                        # reported as wrong ISRC codes. It is unclear what
                                        # needs to be done with those.
                                        # first get rid of cruft
                                        value_upper = identifier.get('value').strip().upper()
                                        isrc_tmp = value_upper
                                        if isrc_tmp.startswith('ISRC'):
                                            isrc_tmp = isrc_tmp.split('ISRC')[-1].strip()
                                        if isrc_tmp.startswith('CODE'):
                                            isrc_tmp = isrc_tmp.split('CODE')[-1].strip()

                                        # Chinese ISRC, see https://www.discogs.com/forum/thread/799845
                                        if '/A.J6' in isrc_tmp:
                                            isrc_tmp = isrc_tmp.rsplit('/', 1)[0].strip()

                                        # replace a few characters
                                        isrc_tmp = isrc_tmp.translate(ISRC_TRANSLATE)
                                        if len(isrc_tmp) != 12:
                                            print_error(counter, 'ISRC (wrong length)', release_id)
                                            counter += 1
                                        else:
                                            valid_isrc = True
                                            if isrc_tmp in isrcs_seen:
                                                print_error(counter, f'ISRC (duplicate {isrc_tmp})', release_id)
                                                counter += 1
                                            else:
                                                isrcs_seen.add(isrc_tmp)

                                            isrcres = re.match(r"\w{5}(\d{2})\d{5}", isrc_tmp)
                                            if isrcres is None:
                                                print_error(counter, 'ISRC (wrong format)', release_id)
                                                counter += 1
                                                valid_isrc = False

                                            if year is not None and valid_isrc:
                                                isrcyear = int(isrcres.groups()[0])
                                                if isrcyear < 100:
                                                    # correct the year. This won't work
                                                    # correctly after 2099.
                                                    if isrcyear <= CURRENT_YEAR - 2000:
                                                        isrcyear += 2000
                                                    else:
                                                        isrcyear += 1900
                                                if isrcyear > CURRENT_YEAR:
                                                    print_error(counter, f'ISRC (impossible year: {isrcyear})', release_id)
                                                    counter += 1
                                                elif year < isrcyear:
                                                    print_error(counter, f'ISRC (date earlier: {isrcyear})', release_id)
                                                    counter += 1

                                            # check the descriptions
                                            # TODO: match with the actual track list
                                            if description_lower != '':
                                                if description_lower in isrc_descriptions_seen:
                                                    print_error(counter, f'ISRC code (description reuse: {description})', release_id)
                                                    counter += 1
                                                isrc_descriptions_seen.add(description_lower)
                                    else:
                                        # specifically check the description
                                        if description_lower != '':
                                            if description_lower.startswith('isrc'):
                                                print_error(counter, f'ISRC Code (in {identifier_type})', release_id)
                                                counter += 1
                                            elif description_lower.startswith('issrc'):
                                                print_error(counter, f'ISRC Code (in {identifier_type})', release_id)
                                                counter += 1
                                            else:
                                                for isrc in discogssmells.isrc_ftf:
                                                    if isrc in description_lower:
                                                        print_error(counter, f'ISRC Code (in {identifier_type})', release_id)
                                                        counter += 1
                                                        break
                                # Label Code
                                if config_settings.label_code:
                                    value = identifier.get('value').lower()
                                    description = identifier.get('description', '').lower()
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

                                        if description in discogssmells.label_code_ftf:
                                            print_error(counter, f"Label Code (in {identifier_type})", release_id)
                                            counter += 1

                                # Matrix / Runout
                                if config_settings.matrix:
                                    value = identifier.get('value')
                                    if identifier_type == 'Matrix / Runout':
                                        for pdmc in discogssmells.pmdc_misspellings:
                                            if pdmc in value:
                                                print_error(counter, 'Matrix (PDMC instead of PMDC)', release_id)
                                                counter += 1
                                        if year is not None:
                                            if 'MFG BY CINRAM' in value and '#' in value and 'USA' not in value:
                                                cinramres = re.search(r'#(\d{2})', value)
                                                if cinramres is not None:
                                                    cinramyear = int(cinramres.groups()[0])
                                                    # correct the year. This won't work correctly after 2099.
                                                    if cinramyear <= CURRENT_YEAR - 2000:
                                                        cinramyear += 2000
                                                    else:
                                                        cinramyear += 1900
                                                    if cinramyear > CURRENT_YEAR:
                                                        print_error(counter, f'Matrix (impossible year: {year})', release_id)
                                                        counter += 1
                                                    elif year < cinramyear:
                                                        print_error(counter, f'Matrix (release date {year} earlier than matrix year {cinramyear})', release_id)
                                                        counter += 1
                                            elif 'P+O' in value:
                                                # https://www.discogs.com/label/277449-PO-Pallas
                                                pallasres = re.search(r'P\+O[–-]\d{4,5}[–-][ABCD]\d?\s+\d{2}[–-](\d{2})', value)
                                                if pallasres is not None:
                                                    pallasyear = int(pallasres.groups()[0])
                                                    # correct the year. This won't work correctly after 2099.
                                                    if pallasyear <= CURRENT_YEAR - 2000:
                                                        pallasyear += 2000
                                                    else:
                                                        pallasyear += 1900
                                                    if pallasyear > CURRENT_YEAR:
                                                        print_error(counter, f'Matrix (impossible year: {year})', release_id)
                                                        counter += 1
                                                    elif year < pallasyear:
                                                        print_error(counter, f'Matrix (release date {year} earlier than matrix year {pallasyear})', release_id)
                                                        counter += 1

                                # Mastering SID Code
                                if config_settings.mastering_sid:
                                    if identifier_type == 'Mastering SID Code':
                                        value = identifier.get('value').strip()
                                        value_lower = identifier.get('value').lower().strip()
                                        if value_lower not in discogssmells.sid_ignore:
                                            # cleanup first for not so heavy formatting booboos
                                            master_sid_tmp = value_lower.translate(SID_TRANSLATE)
                                            res = discogssmells.masteringsidre.match(master_sid_tmp)
                                            if res is None:
                                                print_error(counter, f'Mastering SID Code (illegal value: {value})', release_id)
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
                                    else:
                                        if description_lower in discogssmells.masteringsids:
                                            print_error(counter, 'Mastering SID Code', release_id)
                                            counter += 1
                                        elif description_lower in discogssmells.possible_mastering_sid:
                                            print_error(counter, 'Possible Mastering SID Code', release_id)
                                            counter += 1

                                # Mould SID Code
                                if config_settings.mould_sid:
                                    description = identifier.get('description', '').strip()
                                    description_lower = description.lower()
                                    if identifier_type == 'Mould SID Code':
                                        value = identifier.get('value').strip()
                                        value_lower = identifier.get('value').lower().strip()
                                        if value_lower not in discogssmells.sid_ignore:
                                            # cleanup first for not so heavy formatting booboos
                                            mould_sid_tmp = value_lower.translate(SID_TRANSLATE)
                                            res = discogssmells.mouldsidre.match(mould_sid_tmp)
                                            if res is None:
                                                print_error(counter, f'Mould SID Code (illegal value: {value})', release_id)
                                                counter += 1
                                            else:
                                                if config_settings.mould_sid_strict:
                                                    mould_split = mould_sid_tmp.split('ifpi', 1)[-1]
                                                    for ch in ['i', 'o', 's', 'q']:
                                                        if ch in mould_split[-2:]:
                                                            print_error(counter, f'Mould SID Code (strict value check: {mould_split})', release_id)
                                                            counter += 1
                                                            break
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
                                    else:
                                        if description_lower in discogssmells.mouldsids:
                                            print_error(counter, f'Mould SID Code (in {identifier_type})', release_id)
                                            counter += 1

                                # Mastering SID and Mould SID descriptions
                                if config_settings.mastering_sid or config_settings.mould_sid:
                                    description = identifier.get('description', '').strip()
                                    description_lower = description.lower()
                                    if description_lower in SID_DESCRIPTIONS:
                                        print_error(counter, 'Unspecified SID Code', release_id)
                                        counter += 1

                                # Rights Society
                                if config_settings.rights_society:
                                    value = identifier.get('value')
                                    value_upper = value.upper().strip()
                                    value_upper_translated = value_upper.translate(RIGHTS_SOCIETY_TRANSLATE_QND)

                                    if identifier_type == 'Rights Society':
                                        if not (value_upper in discogssmells.rights_societies or value_upper_translated in discogssmells.rights_societies or value_upper == 'NONE'):

                                            # There are a few known errors for the Rights Society
                                            # field so check those first before moving on to the
                                            # combined fields or the bogus values.
                                            reported = False
                                            errors = check_rights_society(value_upper)
                                            for error in errors:
                                                print_error(counter, f"Rights Society ({error})", release_id)
                                                counter += 1
                                                reported = True

                                            # The field either contains multiple rights societies
                                            # or contains bogus values.
                                            if not reported:
                                                # temporary list to store Rights Society values to check
                                                rights_society_to_check = []

                                                # known delimiters used, sorted in the most useful order
                                                # This is not necessarily the best order or the best split.
                                                # TODO: rework.
                                                split_rs = []
                                                for delimiter in RIGHTS_SOCIETY_DELIMITERS:
                                                    if delimiter in value_upper:
                                                        split_rs = list(map(lambda x: x.strip(), value_upper.split(delimiter)))
                                                        rights_society_to_check = split_rs
                                                        break

                                                rs_determined = 0
                                                for value_rs in rights_society_to_check:
                                                    if value_rs not in discogssmells.rights_societies:
                                                        errors = check_rights_society(value_rs)
                                                        if errors:
                                                            rs_determined += 1
                                                            for error in errors:
                                                                print_error(counter, f"Rights Society ({error})", release_id)
                                                                counter += 1
                                                    else:
                                                        rs_determined += 1

                                                if rs_determined != len(split_rs) and False:
                                                    # TODO: rework, many false positives here
                                                    print_error(counter, f"Rights Society (bogus value: {value})", release_id)
                                                    counter += 1
                                    else:
                                        rs_found = False
                                        if value_upper_translated in discogssmells.rights_societies:
                                            print_error(counter, f"Rights Society ('{value}', in {identifier_type})", release_id)
                                            counter += 1
                                            rs_found = True
                                        elif '/' in value:
                                            possible_rss = value_upper.split('/')
                                            for possible_rs in possible_rss:
                                                if possible_rs.translate(RIGHTS_SOCIETY_TRANSLATE_QND) in discogssmells.rights_societies:
                                                    print_error(counter, f"Rights Society ('{value}', in {identifier_type})", release_id)
                                                    counter += 1
                                                    rs_found = True
                                                    break

                                        if not rs_found:
                                            # check the description of a field
                                            description = identifier.get('description', '').strip().lower()

                                            if description != '':
                                                # squash repeated spaces
                                                description = re.sub(r'\s+', ' ', description)
                                                if description in discogssmells.rights_societies_ftf:
                                                    errors = check_rights_society(value_upper)

                                                    if errors:
                                                        for error in errors:
                                                            print_error(counter, f"Rights Society (in {identifier_type}, {error})", release_id)
                                                            counter += 1
                                                    else:
                                                        print_error(counter, f'Rights Society (in {identifier_type} (description))', release_id)
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
                                        else:
                                            description = identifier.get('description', '').lower()
                                            if description != '':
                                                for spars in discogssmells.spars_ftf:
                                                    if spars in description:
                                                        print_error(counter, f'Possible SPARS Code (in {identifier_type})', release_id)
                                                        counter += 1
                                                        break

                                # debug code to print all descriptions
                                # Useful to find misspellings of various fields
                                # Use with care.
                                #if config_settings.debug:
                                #    description = identifier.get('description', '')
                                #    if description != '':
                                #        print(description, release_id)

                        elif child.tag == 'labels':
                            for label in child:
                                label_id = int(label.get('id', ''))
                                catno = label.get('catno', '').lower()
                                if config_settings.label_name:
                                    # https://vinylanddata.blogspot.com/2018/01/detecting-wrong-label-information-in.html
                                    if label_id == 26905:
                                        print_error(counter, 'Wrong label (London)', release_id)
                                        counter += 1
                                if config_settings.label_code:
                                    # check the catalog numbers for possible false positives,
                                    # but exclude "Loft Classics" and others
                                    if year is None or year > 1970:
                                        if catno.startswith('lc') and label_id not in LABEL_CODE_FALSE_POSITIVES:
                                            if discogssmells.labelcodere.match(catno) is not None:
                                                print_error(counter, f'Possible Label Code (in Catalogue Number: {catno})', release_id)
                                                counter += 1
                                if config_settings.deposito_legal and country == 'Spain':
                                    deposito_legal_found = False
                                    if label_id not in [26617, 60778]:
                                        for d in discogssmells.depositores:
                                            result = d.search(catno)
                                            if result is not None:
                                                for depositovalre in discogssmells.depositovalres:
                                                    if depositovalre.search(catno) is not None:
                                                        deposito_legal_found = True
                                                        break
                                            if deposito_legal_found:
                                                print_error(counter, f'Possible Depósito Legal (in Catalogue Number: {catno})', release_id)
                                                counter += 1
                                                break

                        elif child.tag == 'notes':
                            #if '카지노' in child.text:
                            #    # Korean casino spam that used to pop up
                            #    # every once in a while.
                            #    print_error(counter, "Korean casino spam", release_id)
                            #    counter += 1
                            if country == 'Spain':
                                if config_settings.deposito_legal:
                                    # sometimes "deposito legal" can be found
                                    # in the "notes" section.
                                    content_lower = child.text.lower()
                                    for d in discogssmells.depositores:
                                        result = d.search(content_lower)
                                        if result is not None:
                                            deposito_found_in_notes = True
                                            break

                            # see https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-
                            if config_settings.url_in_html:
                                if '&lt;a href="http://www.discogs.com/release/' in child.text:
                                    print_error(counter, "old link (Notes)", release_id)
                                    counter += 1
                            if config_settings.creative_commons:
                                cc_found = False
                                for cc_ref in discogssmells.creativecommons:
                                    if cc_ref in child.text:
                                        print_error(counter, f"Creative Commons reference ({cc_ref})", release_id)
                                        counter += 1
                                        cc_found = True
                                        break

                                if not cc_found:
                                    if 'creative commons' in child.text.lower():
                                        print_error(counter, "Creative Commons reference", release_id)
                                        counter += 1

                        elif child.tag == 'released':
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

                        elif child.tag == 'tracklist':
                            # check artists and extraartists here TODO
                            if config_settings.tracklisting:
                                # various tracklist sanity checks, but only if there is
                                # only a single format to make things easier. This should be
                                # fixed at some point TODO.
                                #
                                # Currently two checks are supported:
                                #
                                # * tracklist numbering reuse
                                # * not using correct numbering on releases with sides
                                tracklist_positions = set()
                                tracklist_correct = True
                                if len(formats) == 1:
                                    recorded_format = list(formats)[0]
                                    for track in child:
                                        for track_elem in track:
                                            if track_elem.tag == 'position':
                                                if track_elem.text not in [None, '', '-']:
                                                    if num_formats == 1:
                                                        if track_elem.text in tracklist_positions:
                                                            print_error(counter, f'Tracklisting reuse ({recorded_format}, {track_elem.text})', release_id)
                                                            counter += 1
                                                    tracklist_positions.add(track_elem.text)

                                                    if tracklist_correct:
                                                        if recorded_format in TRACKLIST_CHECK_FORMATS:
                                                            try:
                                                                int(track_elem.text)
                                                                print_error(counter, f'Tracklisting uses numbers ({recorded_format})', release_id)
                                                                counter += 1
                                                                tracklist_correct = False
                                                            except ValueError:
                                                                pass

                        if prev_counter != counter:
                            last_release_checked = release_id
                            prev_counter = counter

                    # report DLs found in notes if no other DL was found
                    if not deposito_found and deposito_found_in_notes:
                        print_error(counter, "Depósito Legal (Notes)", release_id)
                        counter += 1

                    # cleanup to reduce memory usage
                    element.clear()

                    if requested_release is not None:
                        if requested_release == release_id:
                            break
    except Exception as e:
        print("Cannot open dump file", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
