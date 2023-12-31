#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright 2017-2023 - Armijn Hemel

import re

# a list to store the regular expression to recognize
# "depósito legal" in the BaOI 'Other' field
depositores = []

# a few variants of "depósito legal" found in the discogs datadump
# All regular expressions are lower case.
# First the most common ones
depositores.append(re.compile(r'depósito legal'))
depositores.append(re.compile(r'deposito legal'))
depositores.append(re.compile(r'de?s?p*ós*i?r?tl?o?i?\s*l+e?g?al?\.?'))
depositores.append(re.compile(r'des?p?os+ito?\s+legt?al?\.?'))
depositores.append(re.compile(r'legal? des?posit'))
depositores.append(re.compile(r'dep\.\s*legal'))
depositores.append(re.compile(r'dip. legal'))
depositores.append(re.compile(r'dip. leg.'))
depositores.append(re.compile(r'dipòsit legal'))
depositores.append(re.compile(r'dipósit legal'))
depositores.append(re.compile(r'dep; legal'))

# then a slew of misspellings and variants
depositores.append(re.compile(r'deposito légal'))
depositores.append(re.compile(r'deposito legál'))
depositores.append(re.compile(r'depósito legl'))
depositores.append(re.compile(r'depósito lgeal'))
depositores.append(re.compile(r'depodito legal\.?'))
depositores.append(re.compile(r'depòsito? legal\.?'))
depositores.append(re.compile(r'déposito legal\.?'))
depositores.append(re.compile(r'depós?tio legal\.?'))
depositores.append(re.compile(r'dep\.?\s*legal\.?'))
depositores.append(re.compile(r'd\.?\s*legal\.?'))
depositores.append(re.compile(r'de?pto\.?\s*legal\.?'))
depositores.append(re.compile(r'depótiso legal'))
depositores.append(re.compile(r'depósitio legal'))
depositores.append(re.compile(r'depósiti legal'))
depositores.append(re.compile(r'deposrito legal'))
depositores.append(re.compile(r'deoósito legal'))
depositores.append(re.compile(r'depóaito legal'))
depositores.append(re.compile(r'depõsito legal'))
depositores.append(re.compile(r'depñosito legal'))
depositores.append(re.compile(r'deposiro legal\.?'))
depositores.append(re.compile(r'depósito légal'))
depositores.append(re.compile(r'déposito légal'))
depositores.append(re.compile(r'd\.\s*l\.'))
depositores.append(re.compile(r'dep\.\s*leg\.'))
depositores.append(re.compile(r'dep.\s*l.'))
depositores.append(re.compile(r'deposito lagal'))
depositores.append(re.compile(r'depósito lagal'))
depositores.append(re.compile(r'depósito degal'))
depositores.append(re.compile(r'depósito leagal'))
depositores.append(re.compile(r'depóosito legal'))
depositores.append(re.compile(r'depósite legal'))
depositores.append(re.compile(r'sepósito legal'))
depositores.append(re.compile(r'deopósito legal'))
depositores.append(re.compile(r'depásito legal'))
depositores.append(re.compile(r'depôsito legal'))
depositores.append(re.compile(r'depỏsito legal'))
depositores.append(re.compile(r'dep\'osito legal'))
depositores.append(re.compile(r'legal? des?posit'))
depositores.append(re.compile(r'legak des?posit'))
depositores.append(re.compile(r'legai des?posit'))
depositores.append(re.compile(r'legal depos?t'))
depositores.append(re.compile(r'legal dep\.'))

# basque DL:
# http://www.euskadi.eus/deposito-legal/web01-a2libzer/es/impresion.html
depositores.append(re.compile(r'l\.g\.'))

depositovalres = []
# deposito values, probably does not capture everything
depositovalres.append(re.compile(r'[abcjlmopstvz][\s\.\-/_:]\s*\d{0,2}\.?\d{2,3}\s*[\-\./_]\s*(?:19|20)?\d{2}'))
depositovalres.append(re.compile(r'(?:ab|al|as|av|ba|bi|bu|cc|ca|co|cr|cs|gc|gi|gr|gu|hu|le|lr|lu|ma|mu|na|or|pm|po|sa|se|sg|so|ss|s\.\s.|te|tf|t\.f\.|to|va|vi|za)[\s\.\-/_:]\s*\d{0,2}\.?\d{2,3}\s*[\-\./_]\s*(?:19|20)?\d{2}'))

# label code
#labelcodere = re.compile(r'\s*(?:lc)?\s*[\-/]?\s*\d{4,5}')
labelcodere = re.compile(r'\s*(?:lc)?\s*[\-/]?\s*\d{4,6}$')

masteringsidre = re.compile(r'\s*(?:ifpi)?\s*l\w{3,4}$')
mouldsidre = re.compile(r'\s*(?:ifpi)?\s*\w{4,5}$')

# https://en.wikipedia.org/wiki/SPARS_code
# also include 4 letter code, even though not officially a SPARS code
# Some people use "Sony distribution codes" in the SPARS field:
# https://www.discogs.com/forum/thread/339244
validsparscodes = set(['aaa', 'aad', 'add', 'ada', 'daa',
                       'ddd', 'dad', 'dda', 'dddd', 'ddad'])

spars_ftf = set(["spars code", "spar code", "spars-code", "spare code",
                 "sparse code", "sparc code", "spars.code", "sparcs",
                 "sparsc code", "spard code", "sparks code", "sparrs code",
                 "sparscode", "sparce code", "saprs-code", "saprs code",
                 "sars code", "sprs code", "spas code", "pars code",
                 "spars  code", "sparr code", "sparts code", "spras code",
                 "spars cod", "spars cde", "spars cpde", "spars cods",
                 "spars codde", "spars ccde", "spars coe", "spars coce",
                 "spars coda", "spars"])

label_code_ftf = set(['label code', 'labelcode', 'lbel code',
                      'laabel code', 'labe code', 'laberl code'])

isrc_ftf = set(['international standard recording code',
                'international standard recording copyright',
                'international standart recording code', 'isrc', 'irsc',
                'iscr', 'international standard code recording', 'i.s.r.c.',
                'icrs', 'international recording standard code', "isr code"])

# a few rights societies from https://www.discogs.com/help/submission-guidelines-release-country.html
rights_societies = set(["BEL BIEM", "BIEM", "ACAM", "ACDAM", "ACUM", "ADDAF", "AEPI",
                        "ΑΕΠΙ", "AGADU", "AKKA/LAA", "AKM", "ALBAUTOR",
                        "AMCOS", "APA", "APDASPAC", "APDAYC", "APRA",
                        "ARTISJUS", "ASCAP", "AUSTROMECHANA", "BMI", "BUMA",
                        "CAPAC", "CASH", "CEDAR", "CISAC", "CMRRA", "COMAR",
                        "COTT", "EAU", "FCA", "FILSCAP", "GEMA", "GESAC",
                        "GESAP", "GRAMO", "GVL", "HDS", "HFA", "IMRO", "IPRS",
                        "JASRAC", "KCI", "KODA", "KOMCA", "LATGA-A", "MACP",
                        "MECOLICO", "MCPS", "MCSC", "MCSK", "MESAM",
                        "MUSICAUTOR", "MUST", "NCB", "n©b", "N©B", "N(C)B",
                        "OSA", "PAMRA", "PPL", "PROCAN", "PRS", "RAO", "SABAM",
                        "SACEM", "SACEM Luxembourg", "SACM", "SACVEN",
                        "SADAIC", "SAKOJ", "SAMI", "SAMRO", "SAYCO", "SAZAS",
                        "SBACEM", "SCPP", "SCD", "SDRM", "SEDRIM", "SENA",
                        "SESAC", "SGA", "SGAE", "SIAE", "SIMIM", "SOCAN",
                        "SODRAC", "SOKOJ", "SOZA", "SPA", "STEF", "STEMRA",
                        "STIM", "SUISA", "TEOSTO", "TONO", "UACRR", "UBC",
                        "UCMR-ADA", "ZAIKS", "ZPAV"])

rights_societies_ftf = set(['(right societies)', '(rights society',
                            '(rights society)', 'collection society',
                            'copyright collecting society',
                            'copyright society', 'copyrights society',
                            'italy, the vatican, san marino rights society',
                            'japan rights society', 'japanese rights society',
                            'mecahnical rights', 'mechainical rights',
                            'mechancal rights society',
                            'mechanical (recording) rights',
                            'mechanical copyright protection society',
                            'mechanical rights', 'mechanical rights companies',
                            'mechanical rights society',
                            'mechanical-copyright protection society',
                            'mechanicals rights', 'meechanical rights',
                            'netherlands rights society', 'rhights society',
                            'ricghts societies', 'ricghts society',
                            'righrs society', 'righs society',
                            'righst societies', 'righst society',
                            'right society', "right' s societies",
                            "right's societies", 'righta societies',
                            'rightd dociety', 'righties societies',
                            'rights / society', 'rights sdocieties',
                            'rights sicieties', 'rights siocieties',
                            'rights sociaty', 'rights socieities',
                            'rights socieity', 'rights socierty',
                            'rights sociery', 'rights societe',
                            'rights societeis', 'rights societiers',
                            'rights societies', 'rights societiy',
                            'rights societry', 'rights societty',
                            'rights society', 'rights society.',
                            'rights socirty', 'rights socitees',
                            'rights socitey', 'rights soctiety',
                            'rights soecieties', 'rights soiety',
                            'rights spciety', 'rights/societies',
                            'rightsd societies', 'rightssocieties',
                            'righty society', 'rigths societies',
                            'rigths society', 'rigts societies',
                            'ritght society', 'roghts society',
                            'societies rights', 'society rights',
                            'sweden rights society', 'uk rights society',
                            'uk rights societies',
                            'zambia music copyright society',
                            'mechanical rights societiy',
                            'mechanical rights societiy',
                            'romanian rights society', 'french rights society',
                            'france rights society', 'rights societies.',
                            "\"rights societies\"", 'nordisk copyright bureau',
                            'nordic copyright bureau', 'mechanical right',
                            'mechan. copyright', 'rights societies, on cd',
                            'rights associations', 'rights association',
                            'original rights', 'rights info'])

# several possible misspellings of rights societies
# Not all of these are necessarily Discogs user errors.
#
# As an example STEMPRA has been used on actual releases:
#
# https://www.discogs.com/release/8578592
# https://www.discogs.com/release/629916
#
# STEMA:
#
# https://www.discogs.com/release/1511006
# https://www.discogs.com/release/529700
#
# There are a few wrong values, but currently they are also triggered
# by correct values, so they are ignored for now.
#rights_societies_wrong = set(['BIE', 'TEMRA', 'STEMR'])
rights_societies_wrong = set(['BOEM', 'BEIM', 'BIME', 'BIEN', 'BIE;', 'BIEIM',
                              'BIEAM', 'BIEEM', 'BIELM', 'BIEL', 'BIEMA',
                              'BIETM', 'BIRM', 'BIER', 'BIERM', 'BIE,', 'BIEW',
                              'BIIEM', 'BJEM', 'BLEM', 'BIJMA', 'BIMA', 'BUMS',
                              'BUMDA', 'BUMRA', 'ETEMRA', 'SEMRA', 'SEMTRA',
                              'STAMRA', 'STEAMRA', 'STREMA', 'STREMRA',
                              'STERMA', 'STERMRA', 'STEMA', 'STERA', 'STETMRA',
                              'STERNA', 'STEMPRA', 'STEMCA', 'STEMPA', 'STEMBRA',
                              'STEMERA', 'STEMTA', 'STEMRS', 'STEMMA', 'STEMRAA',
                              'STEMRE', 'STEMRO', 'STEMPIA', 'STEMTRA', 'STEMEA',
                              'STENRA', 'SREMRA', 'JAIRAC', 'JAJSRAC',
                              'JAMRAC', 'JASPAC', 'JASDAC', 'JASARC', 'JASMAC',
                              'JASNAC', 'JASRACK', 'JASREC', 'JASTAC',
                              'JASTRAC', 'JASRAK', 'JASRC', 'JASRAQ', 'ASRAC',
                              'JASARAC', 'JASCRAC', 'JARAC', 'JSARAC', 'JSRAC',
                              'JASHAC', 'RJASRAC', 'YASRAC', 'GMA', 'GENA',
                              'GAMA', 'GE;A', 'GAME', 'GEMRA', 'GGEMA',
                              'GEMMA', 'GEMNA', 'GENMA', 'GEAM', 'GEEMA',
                              'GEME', 'GEMM', 'GEMS', 'GMEA', 'SSABAM', 'SBAM',
                              'SABBAM', 'SABEM', 'SABAN', 'SABM', 'SABIAM',
                              'SABMA', 'SABAAM', 'SAAM', 'SABNAM', 'SEBAM',
                              'SGEA', 'SGSE', 'MPCS', 'MCPA', 'ACAP', 'ACSAP',
                              'ACSCAP', 'ACASP', 'ASAP', 'ASCA[', 'ASCAF',
                              'ASCA', 'ASCAP_', 'ASCAP,', 'ASCAPE', 'ASCSAP',
                              'ASCVAP', 'ASCASP', 'ASXP', 'ASRTISJUS'])

# a set of rights society names with characters from the wrong character set
rights_societies_wrong_char = set(['ΒΙΕΜ', 'BΙEM', 'BΙΕΜ', 'BIEΜ', 'AEΠΙ',
                                   'AEΠI', 'AΕΠΙ', 'AΕΠI', 'AΕPI', 'AEПI',
                                   'АЕПI', 'PAO', 'PАО', 'РAО', 'РАO', 'PAО',
                                   'PАO', 'РAO'])

# SID codes spellings
# These are all exact matches, as too often there are descriptions, such as
# "near mastering SID code" or similar and using a regular expression would
# lead to many false positives.
# Some of these might seem exactly the same, such as 'mastering sid code'
# and 'mastering sid сode' but they are not, as the latter uses a
# Cyrillic 'с', sigh.
masteringsids = set(['mastering sid code', 'master sid code', 'master sid',
                     'masterung sid code', 'mastrering sid code',
                     'matering sid code', 'sid code mastering',
                     'sid code (mastering)', 'sid code: mastering',
                     'sid code [mastering]', '(sid code, mastering)',
                     'sid code, mastering', 'sid code - mastering',
                     'sid-code, mastering', 'sid code - mastering code',
                     'sid code (mastering code)', 'sid code: mastering code',
                     'sid mastering code', 'sid - mastering code',
                     'sid (mastering code)', 'sid mastetring code',
                     'cd sid master', 'cd sid mastering',
                     'cd sid mastering code', 'cd: sid mastering code',
                     'cd, sid mastering code', 'cd, sid - mastering code',
                     'cds, mastering sid code', 'mastered sid code',
                     'masterd sid code', 'masteirng sid code',
                     'sid master code', 'mastering sid codes', 'mastering sid',
                     'mastering sid-code', 'sid master', 's.i.d. master code',
                     'sid (master)', 'sid mastering', 'sid masterind code',
                     'sid (mastering)', 'cd1 mastering sid code',
                     'cd2 mastering sid code', 'mastering s.i.d. code',
                     'mastering sid code cd2', 'mastering sid code cd3',
                     'cd mastering sid code', 'the mastering sid code',
                     'mastering sid code cd1', 'mastering sid code dvd',
                     'sid code mastering cd1', 'sid mastering code cd 1',
                     'sid mastering code cd1', 'masterring sid code',
                     'cd centre etching - sid mastering code',
                     'mastering sid сode', 'masterin sid code',
                     'cd centre etching - mastering sid code',
                     'sid mastering code cd2', 'master s.i.d.',
                     'master s.i.d. code'])

mouldsids = set(['mould sid code', 'mould sid', 'mold sid', 'mold sid code',
                 'modul sid code', 'moould sid code', 'moudl sid code',
                 'moud sid code', 'moulded sid code', 'mouldering sid-code',
                 'moulding sid code', 'mouldg sid code', 'moulde sid code',
                 'mould sid-code', 'mould sid codes', 'moul sid code',
                 'muold sid code', 'sid code mold', 'sid code mould',
                 'sid-code (mould)', 'sid code: mould', 'sid code, mould',
                 'sid code - mould', 'sid code (moild)', 'sid code [mould]',
                 '(sid code, mould)', 'sid-code, mould', 'sid code (mould)',
                 'sid code - mould code', 'sid code (mould code)',
                 'sid code: mould code', 'sid code moulded',
                 'sid code (moulded)', 'sid code, moulding',
                 'sid code mould (inner ring)',
                 'sid code (mould - inner ring)',
                 'sid code (mould, inner ring)', 'sid code mould - inner ring',
                 'sid (mold code)', 'sid mold code', 'sid moul code',
                 'sid mould', 'sid - mould', 'sid (mould)', 'sid, mould',
                 'sid - mould code', 'sid mould code', 'sid mould code cd1',
                 'sid mould code cd 1', 'sid mould code cd2',
                 'sid mould code cd 2', 'sid mould code disc 1',
                 'sid mould code, disc 1', 'sid mould code - disc 1',
                 'sid mould code disc 2', 'sid mould code, disc 2',
                 'sid mould code - disc 2', 'sid mould code disc 3',
                 'sid mould code - disc 3', 'sid mould code disc 4',
                 'sid mould code disc 5', 'sid mould disc 1',
                 'sid mould disc 2', 'sid mould disc 3', 'sid mould disc 4',
                 'sid mould disc 5', 'sid mould disc 6', 'sid muold code',
                 'sid mouls code', 'cd sid mould', 'cd sid mould code',
                 'cd, sid mould code', 'cd, sid - mould code',
                 'cds, mould sid code', 'mould sid code cd1',
                 'mould sid code cd2', 'sid-code mould',
                 'mould sid code, variant 1', 'mould sid code, variant 2',
                 'mould sid code dvd', 'mould sid code - dvd',
                 'mould sid code [dvd]', 'mould sid code, dvd',
                 'mould sid code (dvd)', 'mould sid code cd', 'mould sid-code',
                 'dvd mould sid code', 'dvd, mould sid code',
                 'dvd (mould sid code)', 'dvd - mould sid code',
                 'cd1 mould sid code', 'cd 1 mould sid code',
                 'cd1 : mould sid code', 'cd1, mould sid code',
                 'cd2 mould sid code', 'cd centre etching - mould sid code',
                 'cd centre etching - sid mould code', 'mould sid. code',
                 'mould sid code, both discs', 'cd mould (sid)',
                 'cd mould sid', 'cd mould sid code', 'cd - mould sid code',
                 'cd: mould sid code', 'cd mould, sid code',
                 'cd (mould sid code)', 'cd, mould sid code',
                 'disc 1 mould (sid)', 'disc 1 mould sid code',
                 'disc 1 (mould sid code)', '(disc 1) mould sid code',
                 'disc 1 - mould sid code', 'disc (1) - mould sid code',
                 'disc 1 sid code moulded', 'disc 1 sid mould',
                 'disc 1 sid mould code', 'disc 1 - sid mould code',
                 'disc 2 mould sid code', 'disc 2 (mould sid code)',
                 '(disc 2) mould sid code', 'disc (2) - mould sid code',
                 'dvd sid mould code', 'dvd: sid mould code',
                 'dvd1 mould sid code', 'dvd1 sid code mould',
                 'dvd2 mould sid code', 'dvd2 sid code mould',
                 'mould sid code 1', 'mould sid code 2',
                 'mould sid code both discs', 'mould sid code (both discs)',
                 'mould sid code - cd1', 'mould sid code, cd',
                 'mould sid code cd 1', 'mould sid code (cd1)',
                 'mould sid code [cd]', 'mould sid code - cd1',
                 'mould sid code cd1 & cd2', 'mould sid code (cd 2)',
                 'mould sid code (cd2)', 'mould sid code - cd2',
                 'mould sid code disc 2', 'mould sid code dvd1',
                 'mould s.i.d.', 'mould s.i.d. code', 'moulds.i.d. code',
                 's.i.d. mould code', 's.i.d. moulding code',
                 'modul sid code (both discs)'])

# a list of creative commons identifiers
creativecommons = ['CC-BY-NC-ND', 'CC-BY-ND', 'CC-BY-SA', 'ShareAlike']

# values found for barcodes meaning "no barcode"
nobarcode = set(['no barcode', 'without', 'without ean', 'without barcode',
                 'without digits', 'without numbers', 'barcode without numbers',
                 'released without barcode', 'comes without barcode', 'none',
                 'not barcode', 'non', 'none.', '(none)', '[none]', 'non barcode',
                 '\'none\'', '"none"', '-none-', 'none - pre barcode era',
                 'none shown', 'none present', 'not', 'none (promo)',
                 'not on barcode', 'not present', 'none barcode', 'no barcodes',
                 'pre barcode era', 'there is no barcode', 'nobarcode',
                 'no barcode.', '(no barcode)', ': no barcode', '[no barcode]',
                 'no  barcode', 'no barcode !', 'no barcode!',
                 'don\'t have barcode', 'geen barcode', 'bo barcode',
                 'no barcode available', 'no barcode on cover', 'no barcode on disc',
                 'no  barcode on my cover', 'no barcode on slipcase',
                 'no barcode on the back', 'no barcode on the sleeve',
                 'no barcode on this release', 'no barcode on vinyl release',
                 'no barcode or any other identifiers', 'no barcode or catalog number',
                 'no barcode or identifiers', 'no barcode or identifying numbers',
                 'no barcode or other identifications', 'no barcode or other identifier',
                 'no barcode present', 'no barcode (self released)',
                 'no barcode - self released', 'no barcode / self released',
                 'no barcodes or other identifiers',
                 'no barcodes or other identifiers on medium or sleeve',
                 'no barcode version', 'no barcode, white field where it is on regular release',
                 'nor barcode', 'kein barcode', 'no barcode anywhere on cover or media.',
                 'no barcode as test sleeve', 'no barcode (blank field)',
                 'no barcode / blank field', 'no barcode listed',
                 'no barcode (local distribution)',
                 'no barcode no matrices no identifying markers whatsoever',
                 'no barcode on back cover ', 'no barcode on blu-ray',
                 'no barcode on back cover ', 'no barcode on box.',
                 'no barcode (promo)', 'no barcode (promo only)',
                 'no barcode release', 'promo no barcode',
                 'no barcode - cd promotionnel', 'no barcode displayed',
                 'no barcode on back cover ', 'vinyl edition without barcode  ',
                 'no', 'n/a', 'no bar code', 'unknown', 'nil', 'no code',
                 'no bar code present', '(no bar code)', 'no bar code.',
                 'no barcobe', 'no barcde', 'no baracode', 'no baecode',
                 'no bacrode', 'barcode is not available', 'barcode field is blank',
                 'no barecode', 'no bc on release!', 'no barrcode', 'no bardcode',
                 'no barcord', 'no bracode', 'no borcode', 'no contiene cod de barras.',
                 'w/o code',
                ])
