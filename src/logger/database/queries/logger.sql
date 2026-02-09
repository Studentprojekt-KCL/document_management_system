USE logger;

CREATE TABLE logs (
  occured TIMESTAMP,
  message VARCHAR(1024),
  event_type ENUM ('ERROR', 'INFO', 'WARNING', 'DEBUG') NOT NULL DEFAULT 'INFO',
  service VARCHAR(256)
);
