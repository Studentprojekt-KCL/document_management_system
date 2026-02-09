CREATE USER 'logger'@'logger-endpoint';
ALTER USER 'logger'@'logger-endpoint' IDENTIFIED BY 'changeme';

CREATE DATABASE logger;
USE logger;

CREATE TABLE logs (
  time TIMESTAMP,
  message VARCHAR(1024),
  type VARCHAR(32),
  service VARCHAR(256)
);

GRANT INSERT, SELECT, UPDATE ON logger.logs TO 'logger'@'logger-endpoint';
