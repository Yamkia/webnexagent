FROM odoo:19.0
USER root

# Install git and postgresql client for cloning and DB checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends git postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy provisioning script
COPY provision.sh /usr/local/bin/provision.sh
RUN chmod +x /usr/local/bin/provision.sh

# Run provision script which will exec the original `odoo` command afterwards
ENTRYPOINT ["/usr/local/bin/provision.sh"]
CMD ["odoo"]
