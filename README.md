# Elastic-Crawler

Elasticsearch + Kibana + FSCrawler
This project was largely inspired by https://community.hetzner.com/tutorials/deploy-elk-stack-with-docker, just adding the proxy environment variables and continue from there towards integrating the fscrawler tool.

## Installation

run the following setup before running docker compose:

```
mkdir esdata && sudo chown -R 1000:1000 esdata
```

Then create the .env file with the respective

## Known Issues

### Disk Space

Ensure that enough disk space is available. Even though I had 15 Gig of space available, the service failed, but this could have been a temporary issue. Just ensure enough space!

### Password

Don't spam random characters into the password. If you add a dollar sign, this gets interpreted as the starting character for a variable.
