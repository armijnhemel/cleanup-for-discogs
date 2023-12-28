# Cleanup scripts for Discogs

In this repository several files for digging through the Discogs XML dump files
can be found. The main scripts is `cleanup-for-discogs.py` which reads the data
of each release and which runs a few sanity checks.

There are a few other (hackish) scripts to help extract some interesting
statistics, create graphs, and so on.

More background information about these scripts available on my blog:

<https://vinylanddata.blogspot.com/>

## cleanup-for-discogs.py

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
