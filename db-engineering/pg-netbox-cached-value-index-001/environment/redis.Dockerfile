FROM redis@sha256:344e3945a0b431c8ff1eecd58c5573538126bd756f02fc7e218ddf1fc2546366

COPY redis-users.acl /usr/local/etc/redis/users.acl
RUN chmod 444 /usr/local/etc/redis/users.acl

CMD ["redis-server", "--save", "", "--appendonly", "no", "--aclfile", "/usr/local/etc/redis/users.acl"]
