use ma_polls;

set @poll_name = 'aoty2025';

-- Main results
select concat( band_album, ': ', 1st_votes, '-', 2nd_votes, '-', 3rd_votes, '-', 4th_votes, '-', 5th_votes, '-',
               6th_votes, '-', 7th_votes, '-', 8th_votes, '-', 9th_votes, '-', 10th_votes, ' = ', points, 'pts' ) as aoty
from votes_points
where poll_name=@poll_name and vote_count > 1
order by position asc;

-- Rando corner 1 - 10
select band_album as 1st_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 1st_votes = 1 order by band_name asc;
select band_album as 2nd_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 2nd_votes = 1 order by band_name asc;
select band_album as 3rd_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 3rd_votes = 1 order by band_name asc;
select band_album as 4th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 4th_votes = 1 order by band_name asc;
select band_album as 5th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 5th_votes = 1 order by band_name asc;
select band_album as 6th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 6th_votes = 1 order by band_name asc;
select band_album as 7th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 7th_votes = 1 order by band_name asc;
select band_album as 8th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 8th_votes = 1 order by band_name asc;
select band_album as 9th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 9th_votes = 1 order by band_name asc;
select band_album as 10th_randos from votes_points where poll_name=@poll_name and vote_count = 1 and 10th_votes = 1 order by band_name asc;


