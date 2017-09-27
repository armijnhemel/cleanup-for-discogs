#!/usr/bin/python3

## Script to process individual chunks of Discogs data dumps that have been
## cut from the Discogs data dump using xml_split
##
## Example:
## $ mkdir 201708
## $ cd 201708
## $ zcat ../discogs_20170801_releases.xml.gz | xml_split
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017 - Armijn Hemel

import sys, os, hashlib, queue, multiprocessing, shutil, argparse
import xml.dom.minidom

## process each XML chunk:
## * compute the SHA256 of the chunk
## * extract some information from the XML DOM
def processxml(scanqueue, reportqueue, chunkdir):
	while True:
		filename = scanqueue.get()
		xmlfile = open(os.path.join(chunkdir, filename), 'rb')
		xmldata = xmlfile.read()
		xmlfile.close()
		h = hashlib.new('sha256')
		h.update(xmldata)
		filehash = h.hexdigest()
		## create a DOM for the XML snippet
		xmldom = xml.dom.minidom.parseString(xmldata)

		## get the top level element
		try:
			release_elem = xmldom.getElementsByTagName('release')[0]
		except:
			## No need to process the top level out-00.xml file that is
			## generated to help xml_merge
			## put a dummy value into the report queue
			reportqueue.put({})
			scanqueue.task_done()
			continue

		## get the release id
		release_id = release_elem.getAttribute('id')

		## get the status
		release_status = release_elem.getAttribute('status')

		## place holder
		country = ""

		## get the country
		try:
			country_elem = xmldom.getElementsByTagName('country')[0]
			country = country_elem.childNodes[0].data
		except:
			## no country defined
			pass

		try:
			shutil.move(os.path.join(chunkdir, filename), os.path.join(chunkdir, "%s.xml" % release_id))
		except:
			pass

		## get the format
		## TODO

		result = {}
		result['filename'] = "%s.xml" % release_id
		result['filehash'] = filehash
		result['release_status'] = release_status
		result['country'] = country
		reportqueue.put(result)
		scanqueue.task_done()

def writeresults(reportqueue, chunkdir, filterconfig, totallen):
	sha256file = filterconfig['sha256file']

	## files to write data about status to for releases that are not 'Accepted'
	notacceptedfile = filterconfig['notaccepted_file']
	## file to write country specific data to
	countryfile = filterconfig['country_file']
	counter = 0
	while True:
		result = reportqueue.get()
		if result == {}:
			## dummy value from non-valid entries,
			## so just update the counter and continue
			counter += 1
			reportqueue.task_done()
			continue
		filename = result['filename']
		filehash = result['filehash']
		country = result['country']
		release_status = result['release_status']
		sha256file.write("%s\t%s\n" % (filename, filehash))
		if release_status != 'Accepted':
			notacceptedfile.write("%s\t%s\n" % (filename, release_status))
		countryfile.write("%s\t%s\n" % (filename, country))
		counter += 1

		## flush the files after the last result has been processed to
		## prevent results getting lost.
		if counter == totallen:
			sha256file.flush()
			countryfile.flush()
			notacceptedfile.flush()
		reportqueue.task_done()

def main(argv):
	parser = argparse.ArgumentParser()

	## the following options are provided on the commandline
	parser.add_argument("-c", "--config", action="store", dest="cfg", help="path to configuration file", metavar="FILE")
	parser.add_argument("-m", "--month", action="store", dest="month", help="year + month of Discogs dump (example: 201708)", metavar="MONTH")
	args = parser.parse_args()

	month = '201709'
	#month = '201708'
	chunkdir = '/gpl/tmp/discogs/%s' % month
	outdir = '/gpl/tmp/out'

	if not os.path.isdir(chunkdir):
		print("'%s' is not valid" % chunkdir, file=sys.stderr)
		sys.exit(1)
	if not os.path.isdir(outdir):
		print("'%s' is not valid" % outdir, file=sys.stderr)
		sys.exit(1)

	xml_files = os.listdir(chunkdir)

	totallen = len(xml_files)

	## amount of processes to process entries, hardcode
	## to # CPUs -1 for now, as one process will be needed for
	## writing the results
	amount_of_processes = multiprocessing.cpu_count() - 1

	scanmanager = multiprocessing.Manager()

	scanqueue = scanmanager.Queue(maxsize=0)
	reportqueue = scanmanager.Queue(maxsize=0)
	filterconfig = {}
	processpool = []

	for i in range(0,amount_of_processes):
		p = multiprocessing.Process(target=processxml, args=(scanqueue,reportqueue,chunkdir))
		processpool.append(p)

	## open a few files
	sha256file = open(os.path.join(outdir, 'sha256-%s' % month), 'w')
	filterconfig['sha256file'] = sha256file

	countryfile = open(os.path.join(outdir, 'country-%s' % month), 'w')
	filterconfig['country_file'] = countryfile

	notacceptedfile = open(os.path.join(outdir, 'notaccepted-%s' % month), 'w')
	filterconfig['notaccepted_file'] = notacceptedfile

	r = multiprocessing.Process(target=writeresults, args=(reportqueue, chunkdir, filterconfig, totallen))
	processpool.append(r)

	for p in processpool:
		p.start()

	queue_counter = 0
	for i in xml_files:
		queue_counter += 1
		scanqueue.put(i)
		if queue_counter%100000 == 0:
			print("Sent to queue: %d" % queue_counter)
			sys.stdout.flush()
	print("Sent to queue: %d" % queue_counter)
	sys.stdout.flush()

	scanqueue.join()
	reportqueue.join()

	## final flushes for the files, then close them
	sha256file.flush()
	sha256file.close()

	countryfile.flush()
	countryfile.close()

	notacceptedfile.flush()
	notacceptedfile.close()

	## finally terminate all the processes
	for p in processpool:
		p.terminate()

if __name__ == "__main__":
	main(sys.argv)
