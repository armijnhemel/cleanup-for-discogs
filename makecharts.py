#!/usr/bin/env python3

# Tool that grabs output files from cleanup-discogs.py and generates bar charts
# Used for creating bar charts for blog at https://vinylanddata.blogspot.com/

# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0
#
# Copyright 2017-2019 - Armijn Hemel

import argparse
import collections
import math
import os
import sys

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPM
from reportlab.lib import colors

import reportlab.rl_config as rl_config

# Ugly hack to register the right font with the system, because ReportLab
# really wants to find Times-Roman it seems. This is currently hardcoded
# to my Fedora system.
rl_config.T1SearchPath = ["/usr/share/fonts/truetype/liberation/",
                          "/usr/share/fonts/liberation/"]

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# hardcode the fontpath, this is Fedora specific
liberationpath = os.path.join('/usr/share/fonts/liberation', 'LiberationSerif-Regular.ttf')

# register the font as Times-Roman so ReportLab doesn't barf
pdfmetrics.registerFont(TTFont('Times-Roman', liberationpath))


def main(argv):
    parser = argparse.ArgumentParser()

    # the following options are provided on the commandline
    parser.add_argument("-f", "--file", action="store", dest="cleanupfile",
                        help="path to cleanup result file", metavar="FILE")
    parser.add_argument("-o", "--output", action="store", dest="outputfile",
                        help="path to output file", metavar="FILE")
    args = parser.parse_args()

    # path of the gzip compressed releases file
    if args.cleanupfile is None:
        parser.error("cleanup file missing")

    if args.outputfile is None:
        parser.error("output file missing")

    if os.path.isdir(args.outputfile):
        print("outputfile %s is a directory, cannot overwrite" % args.outputfile, file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.cleanupfile):
        print("result file missing", file=sys.stderr)
        sys.exit(1)

    unique_releases = set()
    cleanupfile = open(args.cleanupfile, 'r')

    # store the number of the last release found with a small in the
    # dataset. This is to ensure that the right amount of columns will
    # be generated in the end through an ugly hack
    max_release_number = 0

    # store the release number for releases with a smell
    for l in cleanupfile:
        if 'https://www.discogs.com/release/' in l and ' -- ' in l:
            #release_number = int(l.rsplit('/', 1)[1])
            release_number = int(l.rsplit('/', 1)[1].split()[0])
            max_release_number = max(max_release_number, release_number)
            unique_releases.add(release_number)
        else:
            print(l)
    cleanupfile.close()

    # count the number of releases, with a smell
    statistics = collections.Counter()
    statistics.update(map(lambda x: x//1000000, unique_releases))

    last_index = max_release_number//1000000

    bardata = (sorted(statistics.items()))
    barwidth = 20

    # sometimes some dummy data need to be inserted to
    # ensure that empty bars are generated if needed
    if len(bardata) != last_index:
        for i in range(0, last_index):
            if bardata[i][0] != i:
                for d in range(0, bardata[i][0] - i):
                    bardata.append((i, 0))
                    bardata.sort()

    print("Unique releases:", len(unique_releases))
    print(bardata)

    maximumvalue = max(map(lambda x: x[1], bardata))
    step = int(math.log(maximumvalue, 10))
    valueStep = pow(10, step)

    # calculate a possible good value for startx so labels are not cut off
    startx = max(10 + step * 10, 30)

    # make sure that the chart is large enough
    chartwidth = len(bardata) * barwidth + 10 * len(bardata)
    drawheight = 225
    drawwidth = chartwidth + startx + 20

    # create the drawing that the barchart will be added to
    drawing = Drawing(drawwidth, drawheight)
    barchart = VerticalBarChart()
    barchart.x = startx
    barchart.y = 20
    barchart.height = 200
    barchart.width = chartwidth
    barchart.data = [tuple(map(lambda x: x[1], bardata))]
    barchart.strokeColor = colors.white
    barchart.valueAxis.valueMin = 0
    barchart.valueAxis.labels.fontSize = 16
    barchart.valueAxis.valueMax = maximumvalue
    barchart.valueAxis.valueStep = valueStep
    barchart.categoryAxis.labels.boxAnchor = 'w'
    barchart.categoryAxis.labels.dx = 0
    barchart.categoryAxis.labels.dy = -10
    #barchart.categoryAxis.labels.angle = -90
    barchart.categoryAxis.labels.fontSize = 16
    barchart.categoryAxis.categoryNames = list(map(lambda x: str(x[0]), bardata))
    barchart.barWidth = barwidth

    drawing.add(barchart)
    renderPM.drawToFile(drawing, args.outputfile, fmt='PNG')

if __name__ == "__main__":
    main(sys.argv)
