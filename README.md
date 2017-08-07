# cleanup-for-discogs

Python script to find known "smells" in Discogs database dump files. Prints out URLs of releases to be fixed.

Currently checks the BaOI fields from Discogs and reports errors for (amongst others):

* depósito legal
* SPARS code
* label code
* rights society
