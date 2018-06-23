##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0-only
##
## Copyright 2017 - Armijn Hemel

import re, datetime

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
depositores.append(re.compile(u'dep; legal'))

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

label_code_ftf = set(['label code', 'labelcode', 'lbel code', 'laabel code', 'labe code', 'laberl code'])

isrc_ftf = set(['international standard recording code','international standard recording copyright', 'international standart recording code', 'isrc', 'irsc', 'iscr', 'international standard code recording', 'i.s.r.c.', 'icrs'])

## a few rights societies from https://www.discogs.com/help/submission-guidelines-release-country.html
rights_societies = set(["BIEM", "ACAM", "ACDAM", "ACUM", "ADDAF", "AEPI", "ΑΕΠΙ", "AGADU", "AKKA/LAA", "AKM", "ALBAUTOR", "AMCOS", "APA", "APDASPAC", "APDAYC", "APRA", "ARTISJUS", "ASCAP", "AUSTROMECHANA", "BMI", "BUMA", "CAPAC", "CASH", "CEDAR", "CISAC", "CMRRA", "COMAR", "COTT", "EAU", "FCA", "FILSCAP", "GEMA", "GESAC", "GESAP", "GRAMO", "GVL", "HDS", "HFA", "IMRO", "IPRS", "JASRAC", "KCI", "KODA", "KOMCA", "LATGA-A", "MACP", "MECOLICO", "MCPS", "MCSC", "MCSK", "MESAM", "MUSICAUTOR", "MUST", "NCB", "n©b", "N©B", "N(C)B", "OSA", "PAMRA", "PPL", "PROCAN", "PRS", "RAO", "SABAM", "SACEM", "SACEM Luxembourg", "SACM", "SACVEN", "SADAIC", "SAKOJ", "SAMI", "SAMRO", "SAYCO", "SAZAS", "SBACEM", "SCPP", "SCD", "SDRM", "SEDRIM", "SENA", "SESAC", "SGA", "SGAE", "SIAE", "SIMIM", "SOCAN", "SODRAC", "SOKOJ", "SOZA", "SPA", "STEF", "STEMRA", "STIM", "SUISA", "TEOSTO", "TONO", "UACRR", "UBC", "UCMR-ADA", "ZAIKS", "ZPAV"])

rights_societies_ftf = set(['(right societies)', '(rights society', '(rights society)', 'collection society', 'copyright collecting society', 'copyright society', 'copyrights society', 'italy, the vatican, san marino rights society', 'japan rights society', 'japanese rights society', 'mecahnical rights', 'mechainical rights', 'mechancal rights society', 'mechanical (recording) rights', 'mechanical copyright protection society', 'mechanical rights', 'mechanical rights companies', 'mechanical rights society', 'mechanical-copyright protection society', 'mechanicals rights', 'meechanical rights', 'netherlands rights society', 'rhights society', 'ricghts societies', 'ricghts society', 'righrs society', 'righs society', 'righst societies', 'righst society', 'right society', "right' s societies", "right's societies", 'righta societies', 'rightd dociety', 'righties societies', 'rights / society', 'rights sdocieties', 'rights sicieties', 'rights siocieties', 'rights sociaty', 'rights socieities', 'rights socieity', 'rights socierty', 'rights sociery', 'rights societe', 'rights societeis', 'rights societiers', 'rights societies', 'rights societiy', 'rights societry', 'rights societty', 'rights society', 'rights society.', 'rights socirty', 'rights socitees', 'rights socitey', 'rights soctiety', 'rights soecieties', 'rights soiety', 'rights spciety', 'rights/societies', 'rightsd societies', 'rightssocieties', 'righty society', 'rigths societies', 'rigths society', 'rigts societies', 'ritght society', 'roghts society', 'societies rights', 'society rights', 'sweden rights society', 'uk rights society', 'zambia music copyright society', "mechanical rights societiy", "mechanical rights societiy", "romanian rights society", "french rights society", "france rights society"])

## several possible misspellings of rights societies
## Not all of these are wrong all the time: STEMPRA has been used
## on actual releases:
## https://www.discogs.com/release/8578592
## https://www.discogs.com/release/629916
## STEMA:
## https://www.discogs.com/release/1511006
## https://www.discogs.com/release/529700
rights_societies_wrong = set(['BOEM', 'BEIM', 'BIME', 'BIEN', 'STREMA', 'STERMA', 'STEMA', 'STEMPRA', 'STEMPA', 'STEMBRA', 'STEMERA', 'STEMTA', 'STEMRS', 'STEMMA', 'STEMRE', 'STEMRO', 'STEMPIA', 'STEMTRA', 'JASPAC', 'JASDAC', 'JASARC', 'JASMAC', 'JASNAC', 'JASRAK', 'JASRC', 'JASRAQ', 'JASARAC', 'JASCRAC', 'JARAC', 'JSARAC', 'GENA'])

## a set of rights society names with characters from the wrong character set
rights_societies_wrong_char = set(['ΒΙΕΜ', 'BΙEM', 'BΙΕΜ', 'BIEΜ', 'AEΠΙ', 'AEΠI', 'AΕΠΙ', 'AΕΠI', 'AΕPI', 'AEПI', 'АЕПI', 'PAO', 'PАО', 'РAО', 'РАO', 'PAО', 'PАO', 'РAO'])

## SID codes spellings
## These are all exact matches, as too often there are descriptions, such as "near mastering SID code"
## or similar and using a regular expression would lead to many false positives.
## Some of these might seem exactly the same, such as 'mastering sid code' and 'mastering sid сode' but
## they are not, as the latter uses a Cyrillic 'с', sigh.
masteringsids = set(['mastering sid code', 'master sid code', 'master sid', 'masterung sid code', 'mastrering sid code', 'matering sid code', 'sid code mastering', 'sid code (mastering)', 'sid code: mastering','sid code [mastering]', '(sid code, mastering)', 'sid code, mastering', 'sid code - mastering', 'sid-code, mastering', 'sid code - mastering code', 'sid code (mastering code)', 'sid code: mastering code', 'sid mastering code', 'sid - mastering code', 'sid (mastering code)', 'sid mastetring code', 'cd sid master', 'cd sid mastering', 'cd sid mastering code', 'cd: sid mastering code', 'cd, sid mastering code', 'cd, sid - mastering code', 'cds, mastering sid code', 'mastered sid code', 'masterd sid code', 'masteirng sid code', 'sid master code', 'mastering sid codes', 'mastering sid', 'mastering sid-code', 'sid master', 's.i.d. master code', 'sid (master)', 'sid mastering', 'sid masterind code', 'sid (mastering)', 'cd1 mastering sid code', 'cd2 mastering sid code', 'mastering s.i.d. code', 'mastering sid code cd2', 'mastering sid code cd3', 'cd mastering sid code', 'the mastering sid code', 'mastering sid code cd1', 'mastering sid code dvd', 'sid code mastering cd1', 'sid mastering code cd 1', 'sid mastering code cd1', 'cd centre etching - sid mastering code', 'mastering sid сode', 'masterin sid code', 'masterring sid code', 'cd centre etching - mastering sid code', 'sid mastering code cd2', 'master s.i.d.', 'master s.i.d. code'])

mouldsids = set(['mould sid code', 'mould sid', 'mold sid', 'mold sid code', 'modul sid code', 'moould sid code', 'moudl sid code', 'moud sid code', 'moulded sid code', 'mouldering sid-code', 'moulding sid code', 'mouldg sid code', 'moulde sid code', 'mould sid-code', 'mould sid codes', 'moul sid code', 'muold sid code', 'sid code mold', 'sid code mould', 'sid-code (mould)', 'sid code: mould', 'sid code, mould', 'sid code - mould', 'sid code (moild)', 'sid code [mould]', '(sid code, mould)', 'sid-code, mould', 'sid code (mould)', 'sid code - mould code', 'sid code (mould code)', 'sid code: mould code', 'sid code moulded', 'sid code (moulded)', 'sid code, moulding', 'sid code mould (inner ring)', 'sid code (mould - inner ring)', 'sid code (mould, inner ring)', 'sid code mould - inner ring', 'sid (mold code)', 'sid mold code', 'sid moul code', 'sid mould', 'sid - mould', 'sid (mould)', 'sid, mould', 'sid - mould code', 'sid mould code', 'sid mould code cd1', 'sid mould code cd 1', 'sid mould code cd2', 'sid mould code cd 2', 'sid mould code disc 1', 'sid mould code, disc 1', 'sid mould code - disc 1', 'sid mould code disc 2', 'sid mould code, disc 2', 'sid mould code - disc 2', 'sid mould code disc 3', 'sid mould code - disc 3', 'sid mould code disc 4', 'sid mould code disc 5', 'sid mould disc 1', 'sid mould disc 2', 'sid mould disc 3', 'sid mould disc 4', 'sid mould disc 5', 'sid mould disc 6', 'sid muold code', 'sid mouls code', 'cd sid mould', 'cd sid mould code', 'cd, sid mould code', 'cd, sid - mould code', 'cds, mould sid code', 'mould sid code cd1', 'mould sid code cd2', 'sid-code mould', 'mould sid code, variant 1', 'mould sid code, variant 2', 'mould sid code dvd', 'mould sid code - dvd', 'mould sid code [dvd]', 'mould sid code, dvd', 'mould sid code (dvd)', 'mould sid code cd', 'mould sid-code', 'dvd mould sid code', 'dvd, mould sid code', 'dvd (mould sid code)', 'dvd - mould sid code', 'cd1 mould sid code', 'cd 1 mould sid code', 'cd1 : mould sid code', 'cd1, mould sid code', 'cd2 mould sid code', 'cd centre etching - mould sid code', 'cd centre etching - sid mould code', 'mould sid. code', 'mould sid code, both discs', 'cd mould (sid)', 'cd mould sid', 'cd mould sid code', 'cd - mould sid code', 'cd: mould sid code', 'cd mould, sid code', 'cd (mould sid code)', 'cd, mould sid code', 'disc 1 mould (sid)', 'disc 1 mould sid code', 'disc 1 (mould sid code)', '(disc 1) mould sid code', 'disc 1 - mould sid code', 'disc (1) - mould sid code', 'disc 1 sid code moulded', 'disc 1 sid mould', 'disc 1 sid mould code', 'disc 1 - sid mould code', 'disc 2 mould sid code', 'disc 2 (mould sid code)', '(disc 2) mould sid code', 'disc (2) - mould sid code', 'dvd sid mould code', 'dvd: sid mould code', 'dvd1 mould sid code', 'dvd1 sid code mould', 'dvd2 mould sid code', 'dvd2 sid code mould', 'mould sid code 1', 'mould sid code 2', 'mould sid code both discs', 'mould sid code (both discs)', 'mould sid code - cd1', 'mould sid code, cd', 'mould sid code cd 1', 'mould sid code (cd1)', 'mould sid code [cd]', 'mould sid code - cd1', 'mould sid code cd1 & cd2', 'mould sid code (cd 2)', 'mould sid code (cd2)', 'mould sid code - cd2', 'mould sid code disc 2', 'mould sid code dvd1', 'mould s.i.d.', 'mould s.i.d. code', 'moulds.i.d. code', 's.i.d. mould code', 's.i.d. moulding code', 'modul sid code (both discs)'])

## a list of creative commons identifiers
creativecommons = ['CC-BY-NC-ND', 'CC-BY-ND', 'CC-BY-SA', 'ShareAlike']
