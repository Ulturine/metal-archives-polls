use ma_polls;

set @year = 2025;
set @poll_name = 'aoty2025';

-- Statistics
select count(distinct(album_id)) as album_count from votes_entries where poll_name=@poll_name;
select count(distinct(album_id)) as rando_album_count from votes_points where poll_name=@poll_name and vote_count = 1;
select count(distinct(user_name)) as ballot_count from votes_entries where poll_name=@poll_name;

-- Rando Calrissian Award for "Highest placement with no first place votes"
select position, album_id, band_album as rando_calrissian_award, points from votes_points where poll_name=@poll_name and 1st_votes = 0
order by position asc limit 1;

-- Beltre Award for "earning at least one vote in all ten spots" (with so many votes this is too easy)
select position, album_id, band_album as beltre_award, points from votes_points where poll_name=@poll_name and
       1st_votes > 0 and 2nd_votes > 0 and 3rd_votes > 0 and 4th_votes > 0 and 5th_votes > 0 and
       6th_votes > 0 and 7th_votes > 0 and 8th_votes > 0 and 9th_votes > 0 and 10th_votes > 0
       order by position asc;

-- At Least Somebody Likes Milhouse Award for "lowest placement with at least one first place vote" (non-rando)
select position, album_id, band_album as milhouse_award, points from votes_points where poll_name=@poll_name and 1st_votes > 0 and
       points = ( select min( points ) from votes_points where poll_name=@poll_name and 1st_votes > 0 and vote_count > 1 );

-- 28th
select position, album_id, band_album as slippery_pick_award, points from votes_points where poll_name=@poll_name and position=28;


