  -- Current results up to a day
  set @poll_name = 'aoty2025';
  set @cutoff_date = '2025-12-31'; -- Last day of votes included
  set @cutoff_datetime = DATE_ADD( concat( @cutoff_date, ' 23:59:59' ), INTERVAL 5 HOUR ); -- MA time relative to GMT+8
    
  with top_votes as
  (
    select  poll_name, band_name, album_title,
          concat( band_name,
                  coalesce( concat( ' / ', band_name_2 ), '' ),
                  coalesce( concat( ' / ', band_name_3 ), '' ),
                  coalesce( concat( ' / ', band_name_4 ), '' ),
                  coalesce( concat( ' / ', band_name_5 ), '' ),
                  coalesce( concat( ' / ', band_name_6 ), '' ),
                  coalesce( concat( ' / ', band_name_7 ), '' ),
                  coalesce( concat( ' / ', band_name_8 ), '' ),
                  coalesce( concat( ' / ', band_name_9 ), '' ),
                  coalesce( concat( ' / ', band_name_10 ), '' ),
                  ' - ', album_title ) as band_album,
           sum( case pos when 1 then 25 when 2 then 18 when 3 then 15 when 4 then 12 when 5 then 10
                   when 6 then 8 when 7 then 6 when 8 then 4 when 9 then 2 when 10 then 1 else 0 end ) as points,
         count( * ) as vote_count,
         count( case pos when 1 then pos else NULL end ) 1st_votes,
         count( case pos when 2 then pos else NULL end ) 2nd_votes,
         count( case pos when 3 then pos else NULL end ) 3rd_votes,
         count( case pos when 4 then pos else NULL end ) 4th_votes,
         count( case pos when 5 then pos else NULL end ) 5th_votes,
         count( case pos when 6 then pos else NULL end ) 6th_votes,
         count( case pos when 7 then pos else NULL end ) 7th_votes,
         count( case pos when 8 then pos else NULL end ) 8th_votes,
         count( case pos when 9 then pos else NULL end ) 9th_votes,
         count( case pos when 10 then pos else NULL end ) 10th_votes,
         band_id_2, band_name_2,
         band_id_3, band_name_3,
         band_id_4, band_name_4,
         band_id_5, band_name_5,
         band_id_6, band_name_6,
         band_id_7, band_name_7,
         band_id_8, band_name_8,
         band_id_9, band_name_9,
         band_id_10, band_name_10
  from votes_entries
  where poll_name=@poll_name and submission_date_utc0 <= @cutoff_datetime
  group by poll_name, band_id, album_id, band_name, album_title
  )
  (
    select 'polldate:', date_format( @cutoff_date, '%D %M %Y' )
  )
  union
  (
    select 'ballots:', count( distinct( user_hash_id ) ) from ma_polls.votes_entries
    where poll_name=@poll_name and submission_date_utc0 <= @cutoff_datetime
  ) 
  union
  (
    select band_album, points from top_votes
    order by points desc, vote_count desc,
                   1st_votes desc, 2nd_votes desc, 3rd_votes desc, 4th_votes desc, 5th_votes desc,
                   6th_votes desc, 7th_votes desc, 8th_votes desc, 9th_votes desc, 10th_votes desc, band_name asc
    limit 20 
  )
