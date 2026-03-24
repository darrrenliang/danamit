FROM postgres:17-alpine

RUN apk add --no-cache \
    bash \
    curl \
    unzip \
    gzip \
    aws-cli

WORKDIR /workspace

RUN aws --version && pg_dump --version

CMD ["/bin/bash"]