#!/usr/bin/env python

# Description : Scrapes albums from the Metal Archives web site and writes bands/albums to CSV files

# Modified: 06-Feb-2025 ULT - Added date range args
# Modified: 28-Jan-2025 ULT - Output flat list (one band per line)
# Creation: 04-Jan-2025 ULT

import os
import sys
import csv
import re
import time
from datetime import date
import ma_helper as ma

band_re = re.compile( r'<a href="https://www.metal-archives.com/bands/.*?/(\d+)" title=".*?">(.*?)</a>' ) # Non-greedy, this appears multiple times for splits and possibly collaborations
album_re = re.compile( r'<a href="https://www.metal-archives.com/albums/.*/.*/(\d+)">(.*)</a>' )
date_re = re.compile( r'.* <!-- (\d\d\d\d)-(\d\d)-(\d\d) -->' )

def parse_bands( band_line ):
    bands = []
    bm = band_re.findall( band_line )
    for ( band_id, band_name ) in bm:
        bands.append( { 'id' : band_id, 'name' : band_name.replace( u"\u200b", "" ) } ) # Get rid of zero-width space
    return bands

def parse_album( album_line ):
    album = {}
    am = album_re.search( album_line )
    if am:
        album[ 'id' ] = am[ 1 ]
        album[ 'name' ] = am[ 2 ].replace( u"\u200b", "" ) # Get rid of zero-width space
    return album

def parse_date( date_line ):
    dt = None
    dm = date_re.search( date_line )
    if dm:
        # Month and day can be 0 when not known, use 1
        dt = date( int( dm[ 1 ] ), max( int( dm[ 2 ] ), 1 ), max( int( dm[ 3 ] ), 1 ) )
    return dt

########
# Main #
########

if len( sys.argv ) <= 6:
    raise Exception( "usage: ma_album_scrape.py <start year> <start mon> <end year> <end mon> <band csv> <album csv> [album flat csv]" )

start_year = int( sys.argv[ 1 ] )
start_mon = int( sys.argv[ 2 ] ) if len( sys.argv[ 2 ] ) > 0 else None
end_year = int( sys.argv[ 3 ] )
end_mon = int( sys.argv[ 4 ] ) if len( sys.argv[ 4 ] ) > 0 else None
band_csv = sys.argv[ 5 ]
album_csv = sys.argv[ 6 ]
album_flat_csv = sys.argv[ 7 ] if len( sys.argv ) > 7 else None

for f in [ band_csv, album_csv ]:
    if os.path.exists( f ):
        raise Exception( f"Output file {f} already exists" )

if start_mon is not None or end_mon is not None:
    # Some albums are listed as only released in a year (some have a month but no day, most have day/mon/year)
    print( "**Warning: use blank start and end months to include all albums in a year" )

bands = {}
albums = {}
max_album_bands = 10  # Maximum bands per album (splits etc.)

album_count = 1 # Will be updated from response
albums_retrieved = 0
page = 1
# release_types = [ "full-length", "ep", "demo", "live album", "split" ]
# release_types = [ "full-length", "ep", "demo", "live album", "split", "collaboration" ]
# Release types permitted in AotY polls (no live albums, although possible if new content)
release_types = [ "full-length", "ep", "demo", "split", "collaboration" ]

while albums_retrieved < album_count:
    album_page_data = ma.query_albums( start_year, start_mon, end_year, end_mon, release_types, page )
    if len( album_page_data ) > 0 and 'aaData' in album_page_data and len( album_page_data[ 'aaData' ] ) > 0:
        num_page_albums = len( album_page_data[ 'aaData' ] )
        if 'iTotalRecords' in album_page_data:
            new_album_count = int( album_page_data[ 'iTotalRecords' ] )
            if page > 1 and new_album_count != album_count:
                print( f"Warning: album count changed from {album_count} to {new_album_count}, may miss results" )
            album_count = new_album_count
        print( f"Retrieved {num_page_albums} results for page {page}, albums {albums_retrieved + 1} - {albums_retrieved + num_page_albums} of {album_count}" )
        for album_data in album_page_data[ 'aaData' ]:
            # Splits will have multiple bands
            album_bands = parse_bands( album_data[ 0 ] )
            album = parse_album( album_data[ 1 ] )
            album[ 'release_type' ] = album_data[ 2 ]
            album[ 'release_date' ] = parse_date( album_data[ 3 ] )

            # Add band(s) to list if not already present
            for b in album_bands:
                if b[ 'id' ] not in bands:
                    bands[ b[ 'id' ] ] = b[ 'name' ]

            if album[ 'id' ] in albums:
                # Should never happen
                print( f"Duplicate album returned ({album[ 'id' ]})" )
            else:
                albums_retrieved = albums_retrieved + 1

            album_info = { 'band_id' : album_bands[ 0 ][ 'id' ], \
                           'name' : album[ 'name' ], \
                           'release_type' : album[ 'release_type' ], \
                           'release_date' : album[ 'release_date' ] }

            # Add any additional bands
            for i in range( 1, len( album_bands ) ):
                album_info[ f"band_id_{i + 1}" ] = album_bands[ i ][ 'id' ]

            albums[ album[ 'id' ] ] = album_info

        page = page + 1

        # Try to avoid being a bot
        # time.sleep( 5 )
        time.sleep( 10 )
    else:
        # Finished
        album_count = albums_retrieved

# Write bands and albums to CSV
with open( band_csv, 'w', newline='', encoding='utf-8' ) as csv_fp:
    csv_writer = csv.writer( csv_fp )
    csv_writer.writerow( [ 'Band Id', 'Band Name' ] )
    for band_id in bands:
        csv_writer.writerow( [ band_id, bands[ band_id ] ] )
       
with open( album_csv, 'w', newline='', encoding='utf-8' ) as csv_fp:
    csv_writer = csv.writer( csv_fp )
    # Allow for up to 10 bands per album
    csv_writer.writerow( [ 'Album Id', 'Band Id'] + [ f"Band Id {i}" for i in range( 2, max_album_bands + 1 ) ] + [ 'Album Name', 'Release Type', 'Release Date' ] )
    for album_id, album_details in albums.items():
        csv_writer.writerow( [ album_id, album_details[ 'band_id' ] ] + \
                             [ album_details[ f"band_id_{i}" ] if f"band_id_{i}" in album_details else None for i in range( 2, max_album_bands + 1 ) ] + \
                             [ album_details[ 'name' ], album_details[ 'release_type' ], album_details[ 'release_date' ] ] )

# Write one band per line
if album_flat_csv:
    with open( album_flat_csv, 'w', newline='', encoding='utf-8' ) as csv_fp:
        csv_writer = csv.writer( csv_fp )
        csv_writer.writerow( [ 'Band Id', 'Album Id', 'Band Name', 'Album Name', 'Release Type', 'Release Date' ] )
        for album_id, album_details in albums.items():
            # First band
            csv_writer.writerow( [ album_details[ 'band_id' ], album_id, bands[ album_details[ 'band_id' ] ], album_details[ 'name' ], album_details[ 'release_type' ], album_details[ 'release_date' ] ] )

            # Additional bands
            b = 2
            while f"band_id_{b}" in album_details:
                csv_writer.writerow( [ album_details[ f"band_id_{b}" ], album_id, bands[ album_details[ f"band_id_{b}" ] ], album_details[ 'name' ], album_details[ 'release_type' ], album_details[ 'release_date' ] ] )
                b = b + 1

print( f"Saved {len( albums )} albums across {len( bands )} bands" )

