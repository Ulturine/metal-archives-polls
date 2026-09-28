use ma_polls;

set @year = 2025;
set @poll_name = 'aoty2025';

-- Google sheets publishing

-- User votes, for privacy do not include user name and use user hash id
select @year as year, user_hash_id, submission_date_utc0, band_album, pos,
       album_id, band_id, band_id_2, band_id_3, band_id_4, band_id_5, band_id_6, band_id_7, band_id_8, band_id_9, band_id_10
from votes_entries where poll_name=@poll_name
order by submission_date_utc0, user_hash_id, pos;

-- Album results (same as posted but can see all point tallies and randos are not separate)
select @year as year, band_id, album_id, position, band_name, album_title,
       vote_count, 1st_votes, 2nd_votes, 3rd_votes, 4th_votes, 5th_votes,
       6th_votes, 7th_votes, 8th_votes, 9th_votes, 10th_votes, points,
       band_id_2, band_name_2, band_id_3, band_name_3, band_id_4, band_name_4, band_id_5, band_name_5,
       band_id_6, band_name_6, band_id_7, band_name_7, band_id_8, band_name_8, band_id_9, band_name_9, band_id_10, band_name_10
from votes_points
where poll_name=@poll_name
order by position asc;
