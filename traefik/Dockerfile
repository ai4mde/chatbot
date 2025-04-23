FROM traefik:v3.0

# Create required directories
RUN mkdir -p /etc/traefik/acme && \
    touch /etc/traefik/acme.json && \
    chmod 600 /etc/traefik/acme.json

# Copy configuration
COPY config.yml /etc/traefik/config.yml

# Expose ports
EXPOSE 80 443 8080

# Set entrypoint
ENTRYPOINT ["traefik", "--configfile=/etc/traefik/config.yml"] 