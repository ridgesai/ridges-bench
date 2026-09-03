FROM postgres@sha256:60f4761b9035e0b8d5218f701a8c3382f641bf12b1604822574cf5be3baeb537

COPY postgres-init.sh /docker-entrypoint-initdb.d/10-task-init.sh
RUN chmod 755 /docker-entrypoint-initdb.d/10-task-init.sh
