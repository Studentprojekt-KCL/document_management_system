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
IP_DMISAPI=<IP address for dmis-api container>
IP_FRONTEND=<IP address for front-end container>
IP_CONGITLAB=<IP address for connector-gitlab container>
IP_CONNECTOR_MINIO=<IP address for connector-minio container>
IP_STOCHASTIC_ANALYZER=<IP address for stochastic-analyzer container>

# log-api
LOGAPI_BIND_ADDR=<bind address>
LOGAPI_BIND_PORT=<port number>
LOGAPI_LOGDB_URL=<database host>
LOGAPI_LOGDB_USER=<database username>
LOGAPI_LOGDB_PASSW=<database password>
LOGAPI_LOGDB_DATABASE=<database name>

# log-database
MYSQL_DATABASE=<database name>
MYSQL_USER=<database user>
MYSQL_PASSWORD=<database password>
MYSQL_RANDOM_ROOT_PASSWORD=<true or false>

# search-engine
SEARCHENG_BIND_PORT=<port number>
DMISAPI_CONGATEWAY_URL=<connector service URL>
SEARCHENG_BIND_ADDR=<bind address>

# dmis-api
DMIS_SEARCH_API_URL=<search engine URL>

# front-end
FRONTEND_DMISAPI_URL=<API endpoint URL>
FRONTEND_AD_URL=<keycloak base URL>
FRONTEND_AD_REALM=<keycloak realm>
FRONTEND_AD_CLIENT_ID=<keycloak id>
FRONTEND_DMISAPI_BASE_URL=<api endpoint>

# connector-gitlab
CONGITLAB_BIND_PORT=<port number>
CONGITLAB_GITLAB_URL=<GitLab instance URL>
CONGITLAB_MINIO_ACCESS_ADDRESS=<MinIO access URL>
CONGITLAB_MINIO_USERNAME=<username>
CONGITLAB_MINIO_PASSWORD=<password>
CONGITLAB_BIND_ADDR=<bind address>
CONGITLAB_SYSTEM_NAME:<system name>

# connector-minio
MINIO_ACCESS_ADDRESS_LOCAL=<local access URL>
MINIO_ROOT_USER=<root username>
MINIO_ROOT_PASSWORD=<root password>
MINIO_USERNAME=<username>
MINIO_PASSWORD=<password>

# stochastic-analyzer
STOCHAN_BIND_ADDR=<bind address>
STOCHAN_BIND_PORT=<port number>
STOCHAN_CLASSIFIER_URL=<classifier endpoint URL>
STOCHAN_LLM_URL=<LLM endpoint URL>
STOCHAN_LLM_MODEL=<model name>
STOCHAN_CONGATEWAY_URL=<connector file endpoint URL>
 ``` 
 
 4. Create .env file for Caddy reverse proxy (HTTPS for front-end container)
 ```bash
 touch Caddy-front-end/.env
 ```
 
 5. Insert env vars for Caddy container 
 
 For now they are duplicates, will be fixed later
 ```
 # Caddy-front-end/.env
CF_API_TOKEN=<API key>
CF_EMAIL=<email>
CLOUDFLARE_EMAIL=<email>
CLOUDFLARE_API_TOKEN=<API key>
ACME_AGREE=true
 ```
 
 6. Log into registry
 ```bash
 docker login registry.dms-lookup.com
 ```
 
 7. Run the stack
 ```bash
 docker compose up
 ```