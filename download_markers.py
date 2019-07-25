#!/usr/bin/env python
# -*- coding: utf-8 -*-

## @package download
# Downloader tool without GUI
# A modified version that uses the markers file to decide what to download.

import sys
import os
import signal
import re
import math

from gmapcatcher.mapUtils import *
from gmapcatcher.mapConf import MapConf
from gmapcatcher.mapArgs import MapArgs
from gmapcatcher.mapServices import MapServ
from gmapcatcher.mapDownloader import MapDownloader
from gmapcatcher.xmlUtils import load_gpx_coords

from scipy import interpolate
import numpy as np

def dl_callback(*args, **kwargs):
    if not args[0]:
        sys.stdout.write('\b=*')

def download(downloader, args, mConf):
    for zl in range(args.max_zl, args.min_zl - 1, -1):
        sys.stdout.write("\nDownloading zl %d \t" % zl)
        downloader.query_region_around_location(
            args.lat, args.lng,
            args.lat_range * 2, args.lng_range * 2, zl,
            args.layer, dl_callback,
            conf=mConf
        )
        downloader.wait_all()

def download_coordpath(downloader, args, mConf):
    coords = load_gpx_coords(args.gpx)
    for zl in range(args.max_zl, args.min_zl - 1, -1):
        sys.stdout.write("\nDownloading zl %d \t" % zl)
        downloader.query_coordpath(coords, zl, args.width, args.layer, dl_callback, conf=mConf)
        downloader.wait_all()

def get_args(sys_argv):
    args = MapArgs(sys_argv)
    if (args.location is None) and (args.gpx is None) and ((args.lat is None) or (args.lng is None)):
        args.print_help()
        os.kill(os.getpid(), signal.SIGTERM)
        sys.exit(0)

    if ((args.lat is None) or (args.lng is None)) and (args.gpx is None):
        locations = ctx_map.get_locations()
        if (not args.location in locations.keys()):
            args.location = ctx_map.search_location(args.location)
            if (args.location[:6] == "error="):
                print args.location[6:]
                sys.exit(0)

        coord = ctx_map.get_locations()[args.location]
        args.lat = coord[0]
        args.lng = coord[1]

    if args.gpx:
        # GPX path mode
        args.width = int(args.width)
        if args.width < 0:
            args.width = 2  # The default for GPX
    else:
        if args.width > 0:
            args.lng_range = km_to_lon(args.width, args.lat)
        if args.height > 0:
            args.lat_range = km_to_lat(args.height)
    return args

def hypot( start, end ):
    return math.hypot( start[0] - end[0], start[1] - end[1] )

def split(start, end, segments):
    x_delta = (end[0] - start[0]) / float(segments)
    y_delta = (end[1] - start[1]) / float(segments)
    points = []
    for i in range(1, segments):
        points.append([start[0] + i * x_delta, start[1] + i * y_delta])
    return [start] + points + [end]

def parse_markers( marker_path ):
    """ marker="63.7363396991_-20.2203369141"   lat="63.736340" lng="-20.220337"    zoom="11"
    """

    markers = []
    lat_regex = re.compile("lat=\"([-0-9.]+)\"")
    lon_regex = re.compile("lng=\"([-0-9.]+)\"")
    with open(marker_path, 'rb') as f:
        for line in f:
            if not line.startswith("#"):
                lat = lat_regex.search(line)
                lon = lon_regex.search(line)
                if lat is None or lon is None:
                    continue
                lat = float(lat.group(1))
                lon = float(lon.group(1))
                markers.append( [lat, lon] )
    return markers

if __name__ == "__main__":

    mConf = MapConf()
    ## Here we can overwrite some of the config values
    print( "Map Service: {}".format( mConf.map_service ) )
    # print mConf.repository_type
    ctx_map = MapServ(mConf)

    args = get_args(sys.argv)

    if (args.location is None):
        args.location = "somewhere"
    else:
        print "location = %s" % args.location

    if args.gpx is None:
        print "Download %s (%f, %f), range (%f, %f), mapsource: \"%s %s\", zoom level: %d to %d" % \
                (args.location, args.lat, args.lng,
                 args.lat_range, args.lng_range,
                 '', '',
                 args.max_zl, args.min_zl)
    else:
        print "Download path in %s, mapsource: \"%s %s\", zoom level: %d to %d, width=%d tiles" % \
                (args.gpx, '', '', args.max_zl, args.min_zl, args.width)


    markers = parse_markers( "/net/n/swgrp/salamon/gmc_data/markers" )
    print( "Markers: {}\n".format( markers ) )
    first = markers.pop(0)
    for second in markers:
        print( "{} -> {}:".format( first, second ) )
        segs = int(hypot( first, second ) / 0.1 )
        print( "    #segs: {}".format( segs ) )
        if segs < 1:
            segs = 1
        pts = split( first, second, segs )
        for pt in pts:
            print( "    {}".format( pt ) )
            downloader = MapDownloader(ctx_map, args.nr_threads)
            try:
                args.lat = pt[0]
                args.lng = pt[1]
                download(downloader, args, mConf)
            finally:
                downloader.stop_all()
        first = second

    #os.kill(os.getpid(), signal.SIGTERM)
