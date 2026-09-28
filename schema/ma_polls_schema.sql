-- Create new database (ma_polls) for 2025, changes
-- 1) Extra hash_user_id column (since we do not have easy access to forum user id), make this primary key for now
-- 2) Poll table, with poll_id column in votes
-- 3) votes has vote submission date column
-- After creation have to copy data from old database (now renamed ma_aoty_2024), adding in user_hash_ids
use ma_polls;

create table bands( band_id bigint primary key, name varchar(200) not null, alt_name varchar(200));

create table albums (album_id bigint primary key, band_id bigint not null,
                     band_id_2 bigint, band_id_3 bigint, band_id_4 bigint,
                     band_id_5 bigint, band_id_6 bigint, band_id_7 bigint,
                     band_id_8 bigint, band_id_9 bigint, band_id_10 bigint,
                     title varchar(500) not null, alt_title varchar(500),
                     release_type varchar(20), release_date date,
                     constraint fk_albums_band_id foreign key(band_id) references bands(band_id),
                     constraint fk_albums_band_id_2 foreign key(band_id_2) references bands(band_id),
                     constraint fk_albums_band_id_3 foreign key(band_id_3) references bands(band_id),
                     constraint fk_albums_band_id_4 foreign key(band_id_4) references bands(band_id),
                     constraint fk_albums_band_id_5 foreign key(band_id_5) references bands(band_id),
                     constraint fk_albums_band_id_6 foreign key(band_id_6) references bands(band_id),
                     constraint fk_albums_band_id_7 foreign key(band_id_7) references bands(band_id),
                     constraint fk_albums_band_id_8 foreign key(band_id_8) references bands(band_id),
                     constraint fk_albums_band_id_9 foreign key(band_id_9) references bands(band_id),
                     constraint fk_albums_band_id_10 foreign key(band_id_10) references bands(band_id));

create table users (user_id bigint, user_hash_id bigint primary key, name varchar(60) not null);

create table polls( poll_id bigint primary key, name varchar(60) not null, description varchar(500) );

create table votes( poll_id bigint not null, user_hash_id bigint not null,
                    submission_date_utc0 datetime, album_id bigint not null, pos int not null,
                    constraint primary key(poll_id, user_hash_id, album_id, pos),
                    constraint fk_votes_poll_id foreign key(poll_id) references polls(poll_id),
                    constraint fk_votes_user_hash_id foreign key(user_hash_id) references users(user_hash_id),
                    constraint fk_votes_album_id foreign key(album_id) references albums(album_id),
                    constraint chk_votes_pos check(pos >=1 and pos <=10));

-- Views for producing results
create view votes_entries as
  select p.name as poll_name, u.user_hash_id, u.name as user_name, b.band_id, b.name as band_name,
         a.album_id, a.title as album_title,
         concat( b.name,
                 coalesce( concat( ' / ', b2.name ), '' ),
                 coalesce( concat( ' / ', b3.name ), '' ),
                 coalesce( concat( ' / ', b4.name ), '' ),
                 coalesce( concat( ' / ', b5.name ), '' ),
                 coalesce( concat( ' / ', b6.name ), '' ),
                 coalesce( concat( ' / ', b7.name ), '' ),
                 coalesce( concat( ' / ', b8.name ), '' ),
                 coalesce( concat( ' / ', b9.name ), '' ),
                 coalesce( concat( ' / ', b10.name ), '' ),
                 ' - ', a.title ) as band_album,
         v.pos, v.submission_date_utc0,
         a.band_id_2, b2.name as band_name_2,
         a.band_id_3, b3.name as band_name_3,
         a.band_id_4, b4.name as band_name_4,
         a.band_id_5, b5.name as band_name_5,
         a.band_id_6, b6.name as band_name_6,
         a.band_id_7, b7.name as band_name_7,
         a.band_id_8, b8.name as band_name_8,
         a.band_id_9, b9.name as band_name_9,
         a.band_id_10, b10.name as band_name_10
  from votes v
  inner join polls p on
     v.poll_id = p.poll_id
  inner join users u on
     v.user_hash_id = u.user_hash_id
  inner join albums a on
     v.album_id = a.album_id
  inner join bands b on
     a.band_id = b.band_id
  left join bands b2 on
     a.band_id_2 = b2.band_id
  left join bands b3 on
     a.band_id_3 = b3.band_id
  left join bands b4 on
     a.band_id_4 = b4.band_id
  left join bands b5 on
     a.band_id_5 = b5.band_id
  left join bands b6 on
     a.band_id_6 = b6.band_id
  left join bands b7 on
     a.band_id_7 = b7.band_id
  left join bands b8 on
     a.band_id_8 = b8.band_id
  left join bands b9 on
     a.band_id_9 = b9.band_id
  left join bands b10 on
     a.band_id_10 = b10.band_id;

-- Build album rank/position into view
create view votes_points as
  select poll_name,
         row_number() over ( partition by poll_name order by
                             points desc, vote_count desc,
                             1st_votes desc, 2nd_votes desc, 3rd_votes desc, 4th_votes desc, 5th_votes desc,
                             6th_votes desc, 7th_votes desc, 8th_votes desc, 9th_votes desc, 10th_votes desc,
                             band_name asc ) as position,
         band_id, album_id, band_name, album_title, band_album,
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
         sum( case pos when 1 then 25 when 2 then 18 when 3 then 15 when 4 then 12 when 5 then 10
                     when 6 then 8 when 7 then 6 when 8 then 4 when 9 then 2 when 10 then 1 else 0 end ) as points,
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
  group by poll_name, band_id, album_id, band_name, album_title;

