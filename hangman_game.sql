drop table players;
create table players (
    player_id integer,
    username varchar(20),
    password varchar(20), 
    score integer
);

drop table words; 
create table words (
    word_id integer,
    word varchar(20)
);