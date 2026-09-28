# Metal Archives Album of the Year Poll
Scripts and database schema to run the Encyclopaedia Metallum (Metal Archives) Album of the Year poll.

This system could theoretically be used to run other (top 10) album polls.

## Context
Each year the Metal Archives forum runs a poll where members votes on the metal album of the year.  
[2025 Poll Rules](https://forum.metal-archives.com/viewtopic.php?t=147647)  
[2025 Poll Results](https://forum.metal-archives.com/viewtopic.php?t=147854)

## Outline
Poll information is stored in a MySQL database and results are dynamically queried from a view. Stored information
- Albums released
- Bands that released an album (up to 10 bands may contribute to an album)
- Polls run
- Users (forum members) who voted in a poll
- Ballot votes for a poll

The process starts with CSVs of valid albums for the poll and the bands that released them. As the poll progresses, received vote PMs are exported as XML and processed by a script that attempts to match positions and albums, outputting CSVs for accepted and rejected ballots. The matching attempts to standardise names (.e.g. removing multiple spaces, diacritics) and uses a fuzzy matching library to ignore minor typos.

Rejected ballots are examined by eye and corrected where obvious or pushed back to the submitter if not. Corrected votes are placed in a CSV which the script will use to override the XML content.

The final album, band, user and ballot CSVs are manually imported into the database.

## Schema
- `ma_polls_schema.sql`: Creates tables and views in a database
  - bands: table of bands that contributed to an album
  - albums: table of released albums with type and date
  - polls: table of polls run
  - users: table of users who voted in a poll
  - votes: table of user votes in polls
  - vote_entries: view of votes table with poll/album/band/user names alongside ids
  - vote_points: view of albums tallied by vote points and assigned position rank

## Scripts
- `ma_helper.py`: Helper module
- `ma_album_scrape.py`: Uses the album search REST API to scrape albums released between two dates, producing band and album CSV files
- `ma_poll_parse_message_votes.py`: Parses exported XML of PMed ballots and validates the votes against CSVs of released albums. Outputs CSVs of accepted votes, rejected votes and the users who voted.

## Result Importing
Currently imported by hand rather than through a Python script. The importing (bands, albums, users and votes) can be done in sections as the poll progresses (and as new albums are released).

**Poll**
```
-- Create poll
MariaDB> use ma_polls;
MariaDB> insert into ma_polls.polls values( 2, 'aoty2025', 'AOTY 2025 official poll' );
```

**Bands**
```
-- Bands, ignore duplicates
MariaDB> use ma_polls;
MariaDB> SET GLOBAL local_infile=1;
MariaDB> LOAD DATA LOCAL INFILE '/home/ulterine/Documents/MetalArchives/aoty2025/album_bands_20251226.csv'
         IGNORE
         INTO TABLE bands
         FIELDS TERMINATED BY ','
         ENCLOSED BY '"'
         LINES TERMINATED BY '\r\n'
         IGNORE 1 ROWS
         (band_id, name);
```

**Albums**
```
-- Albums
MariaDB> use ma_polls;
MariaDB> SET GLOBAL local_infile=1;
MariaDB> LOAD DATA LOCAL INFILE '/home/ulterine/Documents/MetalArchives/aoty2025/album_albums_20251226.csv'
         INTO TABLE albums
         FIELDS TERMINATED BY ','
         ENCLOSED BY '"'
         LINES TERMINATED BY '\r\n'
         IGNORE 1 ROWS
         (album_id, band_id, @band_id_2, @band_id_3, @band_id_4, @band_id_5, @band_id_6, @band_id_7, @band_id_8, @band_id_9, @band_id_10, title, release_type, release_date)
         SET band_id_2 = NULLIF( @band_id_2, '' ),
             band_id_3 = NULLIF( @band_id_3, '' ),
             band_id_4 = NULLIF( @band_id_4, '' ),
             band_id_5 = NULLIF( @band_id_5, '' ),
             band_id_6 = NULLIF( @band_id_6, '' ),
             band_id_7 = NULLIF( @band_id_7, '' ),
             band_id_8 = NULLIF( @band_id_8, '' ),
             band_id_9 = NULLIF( @band_id_9, '' ),
             band_id_10 = NULLIF( @band_id_10, '' );
```

**Users**
```
-- Users, ignore duplicates
MariaDB> use ma_polls;
MariaDB> SET GLOBAL local_infile=1;
MariaDB> LOAD DATA LOCAL INFILE '/home/ulterine/Documents/MetalArchives/aoty2025/users_final_batch06.csv'
         IGNORE
         INTO TABLE users
         FIELDS TERMINATED BY ','
         ENCLOSED BY '"'
         LINES TERMINATED BY '\r\n'
         IGNORE 1 ROWS
         (user_id, user_hash_id, name);
```

**Votes**
```
MariaDB> use ma_polls;
MariaDB> SET GLOBAL local_infile=1;
MariaDB> LOAD DATA LOCAL INFILE '/home/ulterine/Documents/MetalArchives/aoty2025/votes_accepted_final_batch06.csv'
         INTO TABLE votes
         FIELDS TERMINATED BY ','
         ENCLOSED BY '"'
         LINES TERMINATED BY '\r\n'
         IGNORE 1 ROWS
         (user_hash_id, @dummy_user_name, submission_date_utc0, @dummy_raw_text, @dummy_match_text, album_id, @dummy_band_album, pos, @dummy_match_ratio, @dummy_correction)
         SET poll_id = 2;
```

## Result Querying

- `ma_aoty_poll_results_query.sql`: Contains 1 query for the main results, and 10 for the rando corner results. Each produces a single column suitable for pasting into the forum results post, although need to manually strip the vote counts in the main query for positions 11 onwards.
- `ma_aoty_poll_raw_data_publish.sql`: Contains 2 queries producing results suitable for pasting into the raw data spreadsheet. Only the user hash ids are selected, not user ids or names, to help maintain PM privacy (although with the published repo it would be possible to determine the mappings)
- `ma_aoty_poll_stats_and_awards.sql`: Contains 7 queries for various statistics and awards around the poll (number of albums, ballots, highest place with a single first vote etc.)


## Vote Progression Animation
To see how albums moved in rank as the votes rolled in, there is a query that retrieves the poll state for a particular day,

- `ma_aoty_poll_result_progression.sql`: Retrieves the top 20 albums and their points based on votes up to a particular day.
- `ma_aoty_poll_yyyy_result_progression.html`: Standalone HTML page that animates the movement of albums across the polling period.

The query needs to be run for each day of the poll, and the results pasted into the poll_results array in the HTML file.

