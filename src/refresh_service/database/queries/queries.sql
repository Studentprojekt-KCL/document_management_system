USE tokens;

CREATE TABLE user_sessions (
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  user_id VARCHAR(64),
  service VARCHAR(64),
  token VARCHAR(1024),
  expiry_time TIMESTAMP,
  PRIMARY KEY (user_id, service)
);
