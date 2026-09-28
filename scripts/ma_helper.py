#!/usr/bin/env python

# Description : Module of Metal Archives helper functions

import difflib
import os
import sys
import json
import subprocess
import requests
import urllib.parse

# Modified : 02-Dec-2025 ULT - Now need cookie (login?), matched with user agent to not get 403 due
#                              to Cloudflare protection, may have to add as arg or try playwright
#                            - Do not pass zstd in request header as we cannot handle
# Modified : 06-Feb-2025 ULT - Allow empty months (some albums only have the year as a release date)
# Creation : 04-Jan-2025 ULT

################
# query_albums #
################
def query_albums( start_year, start_month, end_year, end_month, release_types, page, page_size = 200 ):
    albums = []

    if not start_month:
        start_month = ""
    if not end_month:
        end_month = ""

    # Can ignore empty params
    url = f"https://www.metal-archives.com/search/ajax-advanced/searching/albums/?releaseYearFrom={start_year}&releaseMonthFrom={start_month}&releaseYearTo={end_year}&releaseMonthTo={end_month}"

    # As on advanced album search <select>, note options 9 and 11 not present
    release_names = [ "full-length", "live album", "demo", "single", "ep", "video", "boxed set", "split", "HIDDEN", "compilation", "HIDDEN", "split video", "collaboration" ]
    for release_type in release_types:
        try:
            release_type_id = release_names.index( release_type.lower() ) + 1
            url = url + f"&releaseType[]={release_type_id}"
        except ValueError:
            pass

    # iDisplayLength seems to be ignored and hardcoded to 200 but use here
    url = url + f"&iDisplayStart={( page - 1 ) * page_size}&iDisplayLength={page_size}"

    # 2024: Need user agent to avoid 403 (does not need cookie etc)
    # 2025: Need cookie and user agent must match where cookie came from? Now on cloudfare so
    #       requests is fragile. New site also seems to return zstd encoding which (at least
    #       with my install) is not automatically decompressed, so remove from request header,
    #       now get br and r.json() works.
    # TODO: try browser_cookie3 to extract cookie from running browser
    headers = { \
                "Accept" : "application/json, text/javascript, */*; q=0.01", \
                "Accept-Encoding" : "gzip, deflate, br", \
                # "Accept-Encoding" : "gzip, deflate, br, zstd", \
                "Accept-Language" : "en-US,en;q=0.5", \
                "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
                "Cookie" : "masessid=JKTM912684001; login=a0763bc8d0f1b47f4dadf48f1e384966616235; cf_clearance=aRYk5JrnQEKTMaIMiL9tmHtmzNXrVz0SYMVZIFW9CQU-1766229390-1.2.1.1-RDNRPYPMHVNl6Ci78AywKawRWl_9AqCcT45.Pxhp7foGGvy7GgTft3u4Rxa7DJh125JS09waX8M6gfJJJP1WFEe8xLyMTV4QkyEeG8lrRT2qUnLHNOaY08_0RaaB.xBeFS1Bji_1MuS3rrw2Y_FrPOgHUN5jc82Uxrzc84tU2IlWm1wjnVkoLgo8F2OpwfzveJxmW_0gN4DD7JJX7Lr2qNwl.EQYsjgTfDMKaM4xc4w; phpbb3_sj6ou_u=438763; phpbb3_qjy7y_k=872h7gy0r76adhd3; phpbb3_qjyoy_sid=0891be6bc00f573ee2b392a2c8aed46d"
              }

    r = requests.get( url, headers=headers )
    if r.status_code == 200:
        # print( f"Encoding {r.content-encoding}" )
        albums = r.json()
    else:
        try:
        # if r.json() and 'error' in r.json():
            raise Exception( f"Failed to query albums: {r.status_code} ({r.json()[ 'error' ][ 0 : 159 ]})" )
        except:
            raise Exception( f"Failed to query albums: {r.status_code}" )

    return albums


# Fuzzy search for an album
def match_album( album_data, search ):
    pass

