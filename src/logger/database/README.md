# Logger Database

The code in this subdirectory contain the queries and Dockerfile for the logging database.

## Databases

- `logger`, database for the logging service.

### Tables

- `logs`, table containing logs

### Columns

- `logs.id`, log id (integer, auto increment, primary key)
- `logs.message`, log message (varchar 1024)
- `logs.event_type`, log event type (enum (INFO, WARNING, ERROR, DEBUG), not null)
- `logs.service`, from which service (varchar 256)
- `logs.occured`, when it occured (timestamp)

## Configuration

Configuration is done through environment variables.

- `MYSQL_TCP_PORT`, mysql port
- `MYSQL_DATABASE`, database name.
- `MYSQL_USER`, database user.
- `MYSQL_PASSWORD`, user password.
- `MYSQL_RANDOM_ROOT_PASSWORD` / `MYSQL_RANDOM_ROOT_PASSWORD`, MySQL root password.

