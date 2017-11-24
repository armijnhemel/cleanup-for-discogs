# cleanup-for-discogs

Python script to find known "smells" in Discogs database dump files. Prints out URLs of releases to be fixed.

Currently checks the BaOI fields from Discogs and reports errors for (amongst others):

* depósito legal
* SPARS code
* label code
* rights society
* mastering SID code
* mould SID code
* ISRC
* ASIN

It checks the 'notes' field for:

* depósito legal
* old URLs that should be replaced with Discogs format text: https://support.discogs.com/en/support/solutions/articles/13000014661-how-can-i-format-text-

It checks the 'released' field for:

* invalid month (00)
* invalid year

Also included are some checks to cross-correlate the release year with the year embedded in a depósito legal value (Spanish releases only).

Usage:

    $ python3 cleanup-discogs.py -c /path/to/config -d /path/to/discogs/dump

for example:

    $ python3 cleanup-discogs.py -c cleanup.config -d ~/discogs-data/discogs_20170801_releases.xml.gz

More background information about these scripts available on my blog:

https://vinylanddata.blogspot.com/
