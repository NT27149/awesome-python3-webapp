-- schema.sql

drop database if exists awesome;

create database awesome;

use awesome;

create user 'www-data'@'localhost' identified by 'www-data';                            -- 创建新用户
alter user 'www-data'@'localhost' identified with mysql_native_password by 'www-data';  -- 修改密码
grant select, insert, update, delete on awesome.* to 'www-data'@'localhost';            -- 给新用户赋权限（MySQL8.0 后赋权去掉 identified by 'www-data' 否则会报错误

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `passwd` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),  -- 唯一标识数据库表中的每条记录索引
    key `idx_created_at` (`created_at`),  -- 建立索引的意思，也可写成 INDEX `idx_created_at` (``created_at`), 
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),  -- 索引在不读取整个表的情况下，使数据库应用程序可以更快地查找数据，缺点会降低更新表的速度，且会有占用磁盘空间的索引文件
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;