# cleanup-for-discogs

Python script to find known "smells" in Discogs database dump files. Prints out URLs of releases to be fixed.

Currently checks the BaOI fields from Discogs and reports errors for (amongst others):

* depósito legal
* SPARS code
* label code
* rights society
* mastering SID code
* mould SID code

It checks the 'notes' field for:

* depósito legal
* direct links to releases in discogs using url formatting which can possibly be replaced with release formatting

Usage:

    $ python3 cleanup-discogs.py -c /path/to/config -d /path/to/discogs/dump

for example:

    $ python3 cleanup-discogs.py -c cleanup.config -d ~/discogs-data/discogs_20170801_releases.xml.gz

More background information about these scripts available on my blog:

https://vinylanddata.blogspot.com/
