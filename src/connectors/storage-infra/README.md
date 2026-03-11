# Set up
Create a .env file with the following content

    MINIO_ACCESS_ADDRESS=<ADDRESS>
    MINIO_ROOT_USER=<USERNAME>
    MINIO_ROOT_PASSWORD=<PASSWORD>
    MINIO_USERNAME=<USERNAME>
    MINIO_PASSWORD=<PASSWORD>

NOTE; The password must have at least 8 characters

# Build container

    docker build -t dmis-minio .

# Run container

    docker run -d \
      --name minio \
      --env-file .env \
      -p 9000:9000 \
      -v /data/minio:/data \
      dmis-minio
