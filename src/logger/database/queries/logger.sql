USE logger;

CREATE TABLE logs (
  id INT NOT NULL AUTO_INCREMENT,
  occured TIMESTAMP,
  message VARCHAR(1024),
  event_type ENUM ('ERROR', 'INFO', 'WARNING', 'DEBUG') NOT NULL DEFAULT 'INFO',
  service VARCHAR(256),
  PRIMARY KEY (id)
);
