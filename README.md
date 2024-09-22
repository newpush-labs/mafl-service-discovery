# Mafl Service Discovery

Mafl Service Discovery is a tool designed to automatically discover and configure services in a Docker environment. It is inspired by Traefik and provides dynamic service discovery by watching for Docker events and changes in the base configuration file.

## Features
- **Automatic Service Discovery**: Automatically discovers running services based on Docker labels.
- **Dynamic Configuration**: Updates the configuration dynamically as services start, stop, or change.
- **Docker Event Monitoring**: Monitors Docker events to keep the service list up-to-date.
- **Base File Watching**: Watches for changes in the base configuration file and updates accordingly.

## Configuration
Services are configured via Docker labels. The following labels can be used to define a service:
- `mafl.enable`: Set to `true` to enable service discovery for the container.
- `mafl.group`: The group under which the service should be categorized (e.g., Home, Cloud, Docker).
- `mafl.title`: The title of the service.
- `mafl.description`: A brief description of the service.
- `mafl.link`: The URL link to access the service.
- `mafl.icon.name`: The name of the icon to represent the service.
- `mafl.icon.wrap`: Set to `true` to wrap the icon.
- `mafl.icon.color`: The color of the icon.
- `mafl.status.enabled`: Set to `true` to enable status monitoring for the service.
- `mafl.status.interval`: The interval in seconds for status checks.

## Example Docker Compose with Labels:

```yaml
services:
  dozzle:
    image: amir20/dozzle:latest
    container_name: dozzle
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    labels:
      - "com.centurylinklabs.watchtower.enable"
      - "traefik.enable=true"
      - "traefik.http.routers.dozzle.rule=Host(`logs.${DOMAIN}`)"
      - "traefik.http.routers.dozzle.entrypoints=https"
      - "traefik.http.services.dozzle.loadbalancer.server.port=8080"
      - "traefik.http.routers.dozzle.service=dozzle"
      - "traefik.http.routers.dozzle.tls=true"
      - "traefik.http.routers.dozzle.tls.certresolver=default"
      - "traefik.http.routers.dozzle.middlewares=traefik-forward-auth"
      - "mafl.enable=true"
      - "mafl.group=Services"
      - "mafl.title=Dozzle"
      - "mafl.description=Real-time logging and monitoring for Docker in the browser"
      - "mafl.link=https://logs.${DOMAIN}"
      - "mafl.icon.name=devicon:docker"
      - "mafl.icon.wrap=true"
      - "mafl.icon.color=#007acc"
      - "mafl.status.enabled=true"
      - "mafl.status.interval=60"
    restart: unless-stopped
    networks:
      - web

networks:
  web:
    external: true



