FROM ossrs/srs:5

COPY srs.conf /etc/srs/srs.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 1935 8080 8890 1985

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:1985/api/v1/versions || exit 1

ENTRYPOINT ["/entrypoint.sh"]
