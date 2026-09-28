#!/usr/bin/env python

# Description : Reads an xml file of AOTY Metal Archives messages and builds a CSV of votes per user.

# Modified : 10-Dec-2025 ULT - Do not require recipient, stop searching on exact match, check for exact
#                              match before using SequenceMatcher, support vote correction CSV
# Creation : 06-Jan-2025 ULT

import os
import hashlib
import sys
import csv
import re
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
import xml.etree.ElementTree as ET

# You cannot catch all variations, go non-greedy with first .* as most people put the rank first. Use boundary around rank as it really helps, will have to
# tweak the few people not using spaces, i.e. an underscore is not a break.
# [list=[0-9]]   =circle   =square  =disc  =  [a-zA-Z]    spaces not allowed anywhere which is great for re
bbcode_num_list_re = re.compile( r'\[list=[0-9iI]\](.*)' )
# bbcode_list_item_re = re.compile( r'\[\*\](.*)' )

bbcode_url_re = re.compile( r'(\[url=[^]]*\])' )  # Opening url tag

# Note: this re has issues if a band starts with a number (e.g. 1914), grabs the space as only way to match. Not sure why I originally banned digits at the start
# vote_line_re = re.compile( r'(.*?)\s*#?\b(1|01|1st|2|02|2nd|3|03|3rd|4|04|4th|5|05|5th|6|06|6th|7|07|7th|8|08|8th|9|09|9th|10|10th)\b\s*[-:)_\.]?\s*([^0-9].*|$)' )

# Regex notes:
# - the main post-number characters "[-:)_\.=]" match their own boundary, a character like "º" joins the number as a single word so need to match separately for the boundary
# - not sure why I'm non-greedy matching .* at the start, probably leftover from the thread HTML parsing
vote_line_re = re.compile( r'(.*?)\s*#?\b(1|01|1st|2|02|2nd|3|03|3rd|4|04|4th|5|05|5th|6|06|6th|7|07|7th|8|08|8th|9|09|9th|10|10th)[º]?\b\s*[-:)_\.=]?\s*(.*|$)' )

vote_spaces_re = re.compile( r'(\s+)' )
vote_hyphen_re = re.compile( r'(\S)\s*-\s*(\S)' )
vote_self_titled_re = re.compile( r'(.*) - (s\/t|self\s*-?\s*titled)', re.IGNORECASE )

_band_data = None
_album_data = None
_band_album_data = None   # Quick matching of "band - album"
_album_band_data = None   # Quick matching of "album - band"
_band_album_trans = None  # Translation table for normalising band_album string


def parse_args( args : list ):
    bands_csv = None
    albums_csv = None
    vote_corrections_csv = None
    ratio_threshold = 0.95  # difflib returns over 0.50 for very different text, need a high ratio
    users_csv = None
    votes_accepted_csv = None
    votes_rejected_csv = None
    message_xml_files = []

    ArgBands = "--bands-csv="
    ArgAlbums = "--albums-csv="
    ArgVoteCorrections = "--vote-corrections-csv="
    ArgMatchThreshold = "--match-threshold="
    ArgUsers = "--users-csv="
    ArgVotesAccepted = "--votes-accepted-csv="
    ArgVotesRejected = "--votes-rejected-csv="

    for a in args[ 1 : ]:
        if a.lower().startswith( ArgBands ):
            bands_csv = a[ len( ArgBands ) : ]
        elif a.lower().startswith( ArgAlbums ):
            albums_csv = a[ len( ArgAlbums ) : ]
        elif a.lower().startswith( ArgVoteCorrections ):
            vote_corrections_csv = a[ len( ArgVoteCorrections ) : ]
        elif a.lower().startswith( ArgMatchThreshold ):
            ratio_threshold = float( a[ len( ArgMatchThreshold ) : ] )
        elif a.lower().startswith( ArgUsers ):
            users_csv = a[ len( ArgUsers ) : ]
        elif a.lower().startswith( ArgVotesAccepted ):
            votes_accepted_csv = a[ len( ArgVotesAccepted ) : ]
        elif a.lower().startswith( ArgVotesRejected ):
            votes_rejected_csv = a[ len( ArgVotesRejected ) : ]
        else:
            message_xml_files.append( a )

    return( bands_csv, albums_csv, vote_corrections_csv, ratio_threshold, users_csv, votes_accepted_csv, votes_rejected_csv, message_xml_files )


# Initialises album data in memory for searching, dictionary of album ids to list of [ band_id, band_name, album_title ]
def init_album_data( bands_csv, albums_csv ):
    global _band_data
    global _album_data
    global _band_album_data
    global _album_band_data
    global _band_album_trans

    # Set up translation for standardising match strings. Will use later and for quick match, but keep true names in main data.
    in_chars =  "–àáâäåãçðèéêëɡíîïṃñòóôööøṛúûüýąćęłńśÿźż’" # Add to this as we encounter others
    out_chars = "-aaaaaacdeeeegiiimnooooooruuuyacelnsyzz'"

    del_chars = "".join( [ chr( c ) for c in range( 0x300, 0x36f + 1 ) ] ) # Combining diacritic (these add a diacritic to the preceding char, e.g. é is 2 chars)
    _band_album_trans = str.maketrans( in_chars, out_chars, del_chars )

    if not _album_data:
        # Should read from db, just read source CSV for now
        _band_data = dict()
        _album_data = dict()
        _band_album_data = dict()
        _album_band_data = dict()

        # Need band names first
        dt_start = datetime.now()
        with open( bands_csv, newline='', encoding='utf-8' ) as band_fp:
            band_reader = csv.reader( band_fp )
            next( band_reader ) # Skip header
            for row in band_reader:
                _band_data[ row[ 0 ] ] = row[ 1 ]
        dt_end = datetime.now()
        print( f"Read {len( _band_data )} bands in {dt_end - dt_start}" )

        # Read albums, store twice
        #   _album_data: keyed by album id, data list of album title, band_name(s), band_id(s)
        #   _band_album_data: keyed by "band_name(s) - album_name" in lowercase, data album_id
        #   _album_band_data: keyed by "album_name - band_name(s)" in lowercase, data album_id
        dt_start = datetime.now()
        with open( albums_csv, newline='', encoding='utf-8' ) as album_fp:
            album_reader = csv.reader( album_fp )
            next( album_reader ) # Skip header
            for row in album_reader:
                # Store album name, band name (concatenated if multiple) then all 10 (possible) band ids
                album_title = row[ 11 ]
                album_band = _band_data[ row[ 1  ] ]
                for i in range( 2, 11 ):
                    if len( row[ i ] ) > 0:
                        album_band = album_band + " / " + _band_data[ row[ i ] ]
                _album_data[ int( row[ 0 ] ) ] = [ album_title, album_band ] + row[ 1 : 11 ]
                # print( f"_band_album_data[ \"{album_band} - {album_title}\" ] = {int( row[ 0 ] )}" )
                band_album = normalise_band_album( f"{album_band} - {album_title}" )
                if band_album in _band_album_data:
                    # Duplicate release, if this ever happens need to error so it can be manually distinguished somehow
                    raise Exception( f"Duplicate band/album \"{band_album}\", ids {_band_album_data[ band_album ]} and {int( row[ 0 ] )}" )
                _band_album_data[ band_album ] = int( row[ 0 ] )
                _album_band_data[ normalise_band_album( f"{album_title} - {album_band}" ) ] = int( row[ 0 ] )
        dt_end = datetime.now()
        print( f"Read {len( _album_data )} albums in {dt_end - dt_start}" )


# Standardises a band album string for matching. Lowercases, replaces various Latin diacritics with basic glyph characters etc.
def normalise_band_album( band_album : str ) -> str:
    # Single-character translations
    norm_str = band_album.lower().translate( _band_album_trans )

    # Multi-char replacements
    norm_str = norm_str.replace( "æ", "ae" ).replace( "…", "..." )

    # Replace multiple spaces with single
    norm_str = re.sub( vote_spaces_re, " ", norm_str )

    # Hyphens always surrounded by single spaces
    norm_str = re.sub( vote_hyphen_re, r'\1 - \2', norm_str )

    # Replace self-titled designation with band name (this is not handled for cases of album - band)
    norm_str = re.sub( vote_self_titled_re, r'\1 - \1', norm_str )

    # TODO: could go more extreme and stop a lot of manual fixes
    #       - replace & with "and"
    #       - replace other separating characters like ":" all with "-"

    return norm_str

# Converts a text user name to an integer id.
# Note: this is not the true forum user id as that requires doing a post search
# (https://forum.metal-archives.com/search.php?keywords=&terms=all&author=username) and
# parsing the HTML. Here we hash the lowercase username using the shake_256 algorithm
# which supports an output digest length, so restrict to 8 hex characters = an unsigned int.
def user_name_to_id( user_name : str ) -> int:
    test_collision = False
    if test_collision and user_name == 'visionsofsuffering':
        # Force collision for test
        return int( hashlib.shake_256( "jrxcheer".lower().encode( 'utf-8' ) ).hexdigest( 4 ), 16 )

    # hexdigest arg is pairs of bytes so 4 return 00000000 to ffffffff
    return int( hashlib.shake_256( user_name.lower().encode( 'utf-8' ) ).hexdigest( 4 ), 16 )


# Reads a list of XML files of saved messages into a list of dictionaries.
# Keys: recipient, sender, subject, date, message
def read_messages( message_files ):
    messages = []

    for msg_file in message_files:
        tree = ET.parse( msg_file )
        root = tree.getroot()
        msg_num = 0
        for m in root.findall( 'privmsg' ):
            msg_num = msg_num + 1
            recipient = m.find( 'recipient' )
            sender = m.find( 'sender' )
            subject = m.find( 'subject' )
            date = m.find( 'date' )
            msg = m.find( 'message' )
    
            if sender is not None and subject is not None and date is not None and msg is not None:
                # Recipient optional
                if recipient is not None:
                    messages.append( { 'recipient' : recipient.text, 'sender' : sender.text, 'subject' : subject.text, \
                                       'date' : datetime.fromisoformat( date.text ), 'message' : msg.text } )
                else:
                    messages.append( { 'sender' : sender.text, 'subject' : subject.text, \
                                       'date' : datetime.fromisoformat( date.text ), 'message' : msg.text } )
            else:
                print( f"Message {msg_num} in {msg_file} missing components, skipping" )
        
    return messages

# Reads a CSV of manually-corrected votes. Poll runner can update this file after manually fixing votes that fail
# the match threshold.
# CSV should have header line, columns are: User Id,User Name,Band Album Name,Position,Reason
# Returns a dictionary keyed by user name with a dictionary keyed by position with a list of two items [ band_album_name, reason ]
def read_corrected_votes( vote_corrections_csv : str ) -> dict:
    corrected_votes = dict()
    with open( vote_corrections_csv, newline='', encoding='utf-8' ) as vcorr_fp:
        vcorr_reader = csv.reader( vcorr_fp )
        line = 0
        next( vcorr_reader ) # Skip header
        line = line + 1
        for row in vcorr_reader:
            line = line + 1
            if len( row ) == 0:
                continue
            elif len(row) != 5:
                raise Exception( f"Invalid vote correction row on line {line}" )
            user_name = row[ 1 ]
            vote_pos = int( row[ 3 ] )
            if user_name not in corrected_votes:
                corrected_votes[ user_name ] = dict()
            if vote_pos in corrected_votes[ user_name ]:
                raise Exception( f"Duplicate corrected vote {vote_pos} for user {user_name}" )
            else:
                corrected_votes[ user_name ][ vote_pos ] = [ row[ 2 ], row[ 4 ] ]

    return corrected_votes


# Parses a potential vote line for position and attempt to match against known albums,
# storing the result and match ratio in the vote list if it exceeds prior matches
def parse_vote_line( votes : dict, line : str, user_vote_corrections : dict ):
    debug = False
    vm = vote_line_re.match( line )
    if vm:
        # print( f"Vote line: {line}" )
        user_pos = int( ''.join( c for c in vm[ 2 ] if c.isdigit() ) )
        if votes[ user_pos - 1 ][ 3 ] < 1.0: # Proceed only if we do not already have an exact match
            # Check if we have a manual vote correction for this line
            if user_pos in user_vote_corrections:
                user_album = normalise_band_album( user_vote_corrections[ user_pos ][ 0 ] )  # Could consider not normalising
                reason = user_vote_corrections[ user_pos ][ 1 ]
                if True or debug:
                    print( f"Using vote correction for position {user_pos} of {user_album}" )
            else:
                # Regular message vote line
                user_album = normalise_band_album( vm[ 1 ] + vm[ 3 ] )   # Assume user has placed hyphen themselves
                reason = ""

            # Try for exact match first to save a lot of time
            # print( f"user album = {user_album}" )
            if user_album in _band_album_data:
                if debug:
                    print( f"Quick band/album match for pos {user_pos} of {user_album}" )
                votes[ user_pos - 1 ] = [ line, user_album, _band_album_data[ user_album ], 1.0, reason ] # vote text, match text, album id, perfect ratio, correction reason
            elif album_user in _album_band_data:
                if debug:
                    print( f"Quick album/band match for pos {user_pos} of {user_album}" )
                votes[ user_pos - 1 ] = [ line, user_album, _album_band_data[ user_album ], 1.0, reason ] # vote text, match text, album id, perfect ratio, correction reason
            else:
                if debug:
                    print( f"Attempting to fuzzy match \"{user_album}\"" )

                # TODO: should use _band_album_data (and _album_band_data) rather than putting together and normalising every time
                # Search entire dictionary for best match
                for album_id, album_data in _album_data.items():
                    album_title = album_data[ 0 ]
                    album_band = album_data[ 1 ]
    
                    # debug = album_band == "demon bitch" or album_band == "kontact"
   

                    # Try <band> - <album>
                    match_data = normalise_band_album( album_band + " - " + album_title )
                    ratio = SequenceMatcher( None, user_album, match_data ).ratio()
                    if debug:
                        print( f"User pos: {user_pos}" )
                        print( f"Post line: {user_album}" )
                        print( f"Data: {match_data} ({album_band + " - " + album_title})" )
                        print( f"Ratio : {ratio}" )
                    if ratio > votes[ user_pos - 1 ][ 3 ]:
                        if debug:
                            print( f"  Better match '{album_band + " - " + album_title}' ({ratio})" )
                        votes[ user_pos - 1 ] = [ line, user_album, album_id, ratio, reason ]
    
                    # Stop comparing if we found an exact match
                    if votes[ user_pos - 1 ][ 3 ] == 1.0:
                        break
    
                    # Try <album> - <band>
                    match_data = normalise_band_album( album_title + " - " + album_band )
                    ratio = SequenceMatcher( None, user_album, match_data ).ratio()
                    if debug:
                        print( f"User pos: {user_pos}" )
                        print( f"Post line: {user_album}" )
                        print( f"Data: match_data ({album_title + " - " + album_band})" )
                        print( f"Ratio : {ratio}" )
                    if ratio > votes[ user_pos - 1 ][ 3 ]:
                        if debug:
                            print( f"  Better match '{album_title + " - " + album_band}' ({ratio})" )
                        votes[ user_pos - 1 ] = [ line, user_album, album_id, ratio, reason ]
    
                    # Stop comparing if we found an exact match
                    if votes[ user_pos - 1 ][ 3 ] == 1.0:
                        break

# Parses a dictionary of a single message to find AotY votes, returns list of
#   [ user name, vote date, [ list of votes (1 to 10 order) - each vote is a list of four items [ vote raw text, vote match text, album id, match ratio, correction note ], ... ] ]
def parse_message_votes( msg : dict, vote_corrections : dict ):
    user = msg[ 'sender' ]
    vote_date = msg[ 'date' ]

    # Vote text, album id, match ratio and note (for manual correction)
    votes = []
    for i in range( 0, 10 ):
        votes.append( [ "", "", 0, 0.0, "" ] )

    msg_content = msg[ 'message' ]

    # Remove various bbcode tags. Just remove all occurences, do not bother matching pairs
    # Note these should be case-insensitive. Also you seem to be able to put spaces after
    # the left bracket of the opening tag but nowhere else, but assume they have none. 
    msg_content = msg_content.replace( "[b]", "" )
    msg_content = msg_content.replace( "[/b]", "" )
    msg_content = msg_content.replace( "[i]", "" )
    msg_content = msg_content.replace( "[/i]", "" )
    msg_content = msg_content.replace( "[code]", "" )
    msg_content = msg_content.replace( "[/code]", "" )
    msg_content = re.sub( bbcode_url_re, '', msg_content )  # Need to replace [url=...] by re
    msg_content = msg_content.replace( "[/url]", "" )

    using_list = False
    list_item = 0
    for line in msg_content.split( '\n' ):
        line = line.strip()
        m = bbcode_num_list_re.match( line )
        if m:
            using_list = True
            list_item = 0
            line = m[ 1 ].strip()

        if using_list:
            # Looking for [*], may be several on same line
            if line.startswith( '[*]' ) and list_item < 10:
                vote_lines = [ x.strip() for x in line.split( '[*]' ) if len( x ) > 0 ]
                for v in vote_lines:
                    list_item = list_item + 1
                    if list_item <= 10:
                        # Turn into numbered line and match
                        if v.endswith( '[/list]' ):
                            v = v[ : -len( '[/list]' ) ]
                        parse_vote_line( votes, f"{list_item}. {v}", vote_corrections[ user ] if user in vote_corrections else dict() )
                    else:
                        print( f"Discarding extra votes for user {user}" )
                        break
        else:
            # Match line as self-contained (manual number)
            parse_vote_line( votes, line, vote_corrections[ user ] if user in vote_corrections else dict() )

    return user, vote_date, votes

########
# Main #
########

( bands_csv, albums_csv, vote_corrections_csv, ratio_threshold, users_csv, votes_accepted_csv, votes_rejected_csv, message_files ) = parse_args( sys.argv )

if not bands_csv or not albums_csv or not votes_accepted_csv or not votes_rejected_csv or len( message_files ) == 0:
    raise Exception( "usage: ma_poll_parse_message_votes.py --bands-csv=<input file> --albums-csv=<input file> [--vote-corrections-csv=<input file>] [--match-threshold=<match threshold>] [--users-csv=<output file>] --votes-accepted-csv=<output file> --votes-rejected-csv=<output file> <messages xml input file1> [messages xml input file2...]" )

for filename in [ bands_csv, albums_csv, vote_corrections_csv ] + message_files:
    if filename and not os.path.exists( filename ):
        raise Exception( f"Input file {filename} does not exist" )
for filename in [ votes_accepted_csv, votes_rejected_csv, users_csv ]:
    if filename and os.path.exists( filename ):
        raise Exception( f"Output file {filename} already exists, delete before running" )

init_album_data( bands_csv, albums_csv )

users = {}           # Dictionary of user ids keyed by user name (note, using 'hash id' as messages do not contain forum user ids, but name is also unique)
user_hash_ids = {}   # Dictionary of user names keyed by hash ids to check for collisions
vote_dates = {}      # Dictionary of vote dates keyed by user name
votes = {}           # Dictionary of votes keyed by user name
votes_counts = {}    # Dictionary of vote counts keyed by user name (to catch duplicates)
votes_errors = []    # List of failed (not ratio-rejected) votes (dictionary with 'user', 'vote_date', 'votes', 'reason')
votes_corrected = {} # Dictionary of votes (band album name) manually corrected (by poll runner), keyed by user name

dt_start = datetime.now()
messages = read_messages( message_files )
dt_end = datetime.now()
print( f"Read {len(messages)} messages in {dt_end - dt_start}" )

if vote_corrections_csv:
    dt_start = datetime.now()
    votes_corrected = read_corrected_votes( vote_corrections_csv )
    dt_end = datetime.now()
    print( f"Read manual vote corrections in {dt_end - dt_start}" )
else:
    print( f"No manual vote corrections provided" )

print( f"Parsing..." )
parse_start = datetime.now()
for msg in messages:
    user_name, user_vote_date, user_votes = parse_message_votes( msg, votes_corrected )
    user_hash_id = user_name_to_id( user_name )
   
    if user_name in votes_counts:
        # Multiple votes from a user
        votes_counts[ user_name ] = votes_counts[ user_name ] + 1
        print( f"Extra vote message from user {user_name}, discarding both" )
        if user_name in votes: # May have already discarded if 3rd or more vote, only produce error and remove for second vote
            votes_errors.append( { 'user' : user_name, 'vote_date' : vote_dates[ user_name ], 'votes' : votes[ user_name ], 'reason' : 'Multiple vote submissions' } )
            del votes[ user_name ]
            del vote_dates[ user_name ]
        votes_errors.append( { 'user' : user_name, 'vote_date' : user_vote_date, 'votes' : user_votes, 'reason' : 'Multiple vote submissions' } )
    elif user_hash_id in user_hash_ids:
        # Two user names produced the same hash (hopefully never happens)
        orig_user_name = user_hash_ids[ user_hash_id ]
        print( f"Hash collision {user_hash_id} for users {orig_user_name} and {user_name}, discarding both" )
        if orig_user_name in votes: # Move original vote to errors if first collision
            votes_errors.append( { 'user' : orig_user_name, 'vote_date' : vote_dates[ orig_user_name ], 'votes' : votes[ orig_user_name ], 'reason' : f"Hash id collision {user_hash_id}" } )
            del votes[ orig_user_name ]
            del vote_dates[ orig_user_name ]
        votes_errors.append( { 'user' : user_name, 'vote_date' : user_vote_date, 'votes' : user_votes, 'reason' : f"Hash id collision {user_hash_id}" } )
        users[ user_name ] = user_hash_id # Record this for output
    else:
        # Valid vote (structurally)
        print( f"User {user_name}: {user_votes}" )
        users[ user_name ] = user_hash_id
        user_hash_ids[ user_hash_id ] = user_name
        votes[ user_name ] = user_votes
        vote_dates[ user_name ] = user_vote_date
        votes_counts[ user_name ] = 1
parse_end = datetime.now()
print( f"Parsed votes in {parse_end - parse_start}" )

# Write out votes
csv_header = [ 'User Id', 'User Name', 'Vote Date UTC0', 'Vote Raw Text', 'Vote Match Text', 'Album Id', 'Band Album Name', 'Position', 'Match Ratio', 'Correction' ];
with open( votes_accepted_csv, 'w', newline='', encoding='utf-8' ) as va_fp:
    va_writer = csv.writer( va_fp )
    va_writer.writerow( csv_header )
    with open( votes_rejected_csv, 'w', newline='', encoding='utf-8' ) as vr_fp:
        vr_writer = csv.writer( vr_fp )
        vr_writer.writerow( csv_header + [ "Error" ] ) # Extra error column

        for user_name, user_votes in votes.items():
            # Output to accepted or rejected file based on whether we have a complete set of 10 unique albums, all over the match threshold
            all_votes_found = len( [ v for v in votes[ user_name ] if v[ 2 ] > 0 ] ) == 10
            all_votes_match = len( [ v for v in votes[ user_name ] if v[ 3 ] >= ratio_threshold ] ) == 10
            vote_albums = [ v[ 2 ] for v in votes[ user_name ] if v[ 2 ] > 0 ]
            all_votes_unique = len( set( vote_albums ) ) == len( vote_albums )

            vote_date_str = vote_dates[ user_name ].astimezone( timezone.utc ).isoformat() # UTC+0 for the database
            for i in range( 0, len( votes[ user_name ] ) ):
                ( vote_raw_text, vote_match_text, album_id, album_match_ratio, correction_reason ) = votes[ user_name ][ i ]
                band_album_name = f"{_album_data[ album_id ][ 1 ]} - {_album_data[ album_id ][ 0 ]}" if album_id > 0 else ""
                row = [ users[ user_name ], user_name, vote_date_str, vote_raw_text, vote_match_text, album_id, band_album_name, i + 1, album_match_ratio, correction_reason ]
                if all_votes_found and all_votes_match and all_votes_unique:
                    # Accepted ballot
                    va_writer.writerow( row )
                else:
                    # Check individual vote error
                    err = ""
                    if album_id == 0:
                        err = "Missing vote"
                    elif vote_albums.count( album_id ) > 1:
                        err = "Duplicate vote"
                    elif album_match_ratio < ratio_threshold:
                        err = "Insufficient vote match"

                    vr_writer.writerow( row + [ err ] )

        # Write out error votes
        for verr in votes_errors:
            user_name = verr[ 'user' ]
            vote_date_str = verr[ 'vote_date' ].astimezone( timezone.utc ).isoformat()
            for i in range( 0, len( verr[ 'votes' ] ) ):
                ( vote_raw_text, vote_match_text, album_id, album_match_ratio, correction_reason ) = verr[ 'votes' ][ i ]
                band_album_name = f"{_album_data[ album_id ][ 1 ]} - {_album_data[ album_id ][ 0 ]}" if album_id > 0 else ""
                vr_writer.writerow( [ users[ user_name ], user_name, vote_date_str, vote_raw_text, vote_match_text, album_id, band_album_name, i + 1, album_match_ratio, correction_reason, verr[ 'reason' ] ] )

# Output users CSV
if users_csv:
    with open( users_csv, 'w', newline='', encoding='utf-8' ) as u_fp:
        u_writer = csv.writer( u_fp )
        u_writer.writerow( [ 'user_id', 'user_hash_id', 'name' ] )
        for user_name, user_hash_id in users.items():
            u_writer.writerow( [ None, user_hash_id, user_name ] )

