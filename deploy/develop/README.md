# Docker Compose Setup (Macvlan + .env)

## How it works

- All configuration (IPs, ports, credentials) is stored in a `.env` file
- The `docker-compose.yml` uses variable substitution like `${VAR_NAME}`
- Docker Compose automatically loads `.env` from the same directory


## Setup

1. Create the macvlan network

```bash
docker network create -d macvlan \
  --subnet=<Subnet CIDR> \
  --gateway=<Gateway> \
  -o parent=<Parent interface name> \
  dev_net
```

2. Create your `.env` file:

```bash
touch .env
```

3. Insert vars
```
# .env
# IP's for containers
IP_LOG_API=<IP address for log-api container>
IP_LOG_DB=<IP address for log-database container>
IP_SEARCH_ENGINE=<IP address for search-engine container>
IP_DMIS_API=<IP address for dmis-api container>
IP_FRONTEND=<IP address for front-end container>
IP_CONNECTOR_GITLABS=<IP address for connector-gitlabs container>
IP_CONNECTOR_MINIO=<IP address for connector-minio container>
IP_STOCHASTIC_ANALYZER=<IP address for stochastic-analyzer container>

# log-api
LOGGER_BIND_ADDRESS=<bind address, e.g. 0.0.0.0>
LOGGER_PORT=<port number>
LOGGER_DB_HOST=<database host>
LOGGER_DB_USER=<database username>
LOGGER_DB_PASS=<database password>
LOGGER_DB_DATABASE=<database name>

# log-database
MYSQL_DATABASE=<database name>
MYSQL_USER=<database user>
MYSQL_PASSWORD=<database password>
MYSQL_RANDOM_ROOT_PASSWORD=<true or false>

# search-engine
SE_API_PORT=<port number>
SE_API_CONNECTOR_ADDRESS=<connector service URL>
SE_API_HOST=<bind address>

# dmis-api
DMIS_SEARCH_API_URL=<search engine URL>

# front-end
API_HOST=<API endpoint URL>

# connector-gitlabs
GITLAB_CONNECTOR_PORT=<port number>
GITLAB_ADDRESS=<GitLab instance URL>
MINIO_ACCESS_ADDRESS=<MinIO access URL>
MINIO_USERNAME=<username>
MINIO_PASSWORD=<password>

# connector-minio
MINIO_ACCESS_ADDRESS_LOCAL=<local access URL>
MINIO_ROOT_USER=<root username>
MINIO_ROOT_PASSWORD=<root password>
MINIO_USERNAME=<username>
MINIO_PASSWORD=<password>

# stochastic-analyzer
BIND=<bind address>
PORT=<port number>
TEI_URL=<rerank endpoint URL>
CLASSIFIER_URL=<classifier endpoint URL>
MINISTRAL_URL=<LLM endpoint URL>
MINISTRAL_MODEL=<model name>
CONNECTOR_ADDRESS=<connector file endpoint URL>
 ``` 
 
 4. Log into registry
 ```bash
 docker login registry.dms-lookup.com
 ```
 
 4. Run the stack
 ```bash
 docker compose up
 ```