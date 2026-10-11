FROM apache/kafka:3.9.1
USER root
RUN mkdir -p /var/lib/kafka/data && chown -R 1000:1000 /var/lib/kafka
USER 1000
