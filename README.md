# Cleanup scripts for Discogs

In this repository several files for digging through the Discogs XML dump files
can be found. The main scripts is `cleanup-for-discogs.py` which reads the data
of each release and which runs a few sanity checks.

There are a few other (hackish) scripts to help extract some interesting
statistics, create graphs, and so on.

More background information about these scripts available on my blog:

<https://vinylanddata.blogspot.com/>

Why this happens is well explained here:

<https://www.well.com/~doctorow/metacrap.htm>

## cleanup-discogs.py

Python script to find known "smells" in Discogs database dump files. Prints out
URLs of releases to be fixed.

Currently checks the Barcode and Other Identifers (BaOI) fields and reports
errors for (amongst others):

* depósito legal
* SPARS code
* label code
* rights society
* mastering SID code
* mould SID code
* matrix release years (CDs)
* ISRC
* ASIN
* misspelling of Czech characters
* Czechoslovak manufacturing dates
* tracklisting inconsistencies
* Greek license years
* Indian PKD numbers

It checks the 'notes' field for:

* presence of depósito legal
* old URLs that should be replaced with Discogs format text:
  <https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text->

It checks the 'released' field for:

* invalid month (00)
* invalid year

It checks the 'companies' field for:

* pressing plant

Also included are some checks to cross-correlate the release year with the year
embedded in a depósito legal value (Spanish releases only).

Usage:

```console
$ python3 cleanup-discogs.py -c /path/to/config -d /path/to/discogs/dump
```

for example:

```console
$ python3 cleanup-discogs.py -c cleanup.config -d ~/discogs-data/discogs_20170801_releases.xml.gz
```

To check a single release use `-r`:

```console
$ python3 cleanup-discogs.py -c /path/to/config -d /path/to/discogs/dump -r release_number
```

for example:

```console
$ python3 cleanup-discogs.py -c cleanup.config -d ~/discogs-data/discogs_20170801_releases.xml.gz -r 1234
```

In case the number cannot be found the program will exit with an error code
and an error message. Please note that because the Discogs release files are
very big and the file has to be searched from the beginning it can take quite
some time if the release number is a high number.

# List of checks

Below is a list of checks implemented in `cleanup-discogs.py`.

## Depósito Legal

Until August 2017 the "depósito legal" data (mostly used on Spanish releases,
but also on some releases from South America) was essentially free text in the
"Barcode and Other Identifiers" (BaOI) section.

Since July 2017 XML there is a separate field for it and it has become a first
class citizen in BaOI), but there are still many releases where this field has
not yet been used and where the information is in another field instead, such
as "Matrix/Runout", "Label Code" or "Other", with a hint in the "description"
subfield. There are many spellings and misspellings in the "description"
subfield, so the depósito legal isn't always easy to find.

## Label Code

In early Discogs day "Other" was used to specify the label code, but at some
point a dedicated field called "Label Code" was introduced. There are still
many entries that haven't been changed. There are also many users that do not
know what the field "Label Code" means and will put any data found on a label
of a release in this field (instead of the actual label code as specified in
the Discogs guidelines).

## SPARS Code

Like with other fields in the past "Other" was used to specify the SPARS code,
but at some point a dedicated field called "SPARS Code" was introduced. There
are still many entries that haven't been changed though. There are also users
who put the SPARS Code in other places, such as the free text subfield of
"Format", mostly for classical CDs.

## Rights Society

Before a proper "Rights Society" field was created the "Other" field was used to
record the rights society. There are also errors where the Rights Society is
put into other fields such as "ISRC" (due to them being next to each other in
the drop down box to pick the field name when entering data). There are also
many misspellings of the names of rights societies and all kinds of encoding
issues.

## Month checks

In the past it was mandatory to record the month as 00 if it wasn't known
but this is no longer allowed. When saving an entry that has 00 as the
number of the month Discogs will throw an error.

## Regular HTML hyperlinks URLs instead of using markup

In the past it was OK to have normal HTML hyperlinks (in fact it was the only
way to record links), but using regular HTML hyperlinks has been discouraged
and have been replaced by markup:

<https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text->

There are still many releases where old hyperlinks are used.
