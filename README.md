# Elastic-Crawler

Elasticsearch + Kibana + FSCrawler.

This project was largely inspired by https://community.hetzner.com/tutorials/deploy-elk-stack-with-docker, just adding the proxy environment variables and continue from there towards integrating the fscrawler tool.

## Installation

run the following setup before running docker compose:

```
mkdir esdata && sudo chown -R 1000:1000 esdata
```

Then create the .env file with the respective entries. The example.env serves as a template

```
cp example.env .env
```

### FSCrawler

Ensure the following file structure: ('test' is the job_name in this case)

```
.
├── config
│   └── test
│       └── _settings.yaml
├── test-folder
│   └── <your files>
├── external
│   └── <3rd party jars if needed>
├── logs
│   └── <fscrawler logs>
└── docker-compose.yml
```

see also: https://fscrawler.readthedocs.io/en/latest/installation.html#using-docker-compose

Then create the job_name -> \_settings.yaml (no ssl and no ocr for the first test, in order to keep thing simple)

```
---
name: "test"
fs:
  indexed_chars: 100%
  lang_detect: true
  continue_on_error: true
  ocr:
    language: "eng"
    enabled: false
    pdf_strategy: "ocr_and_text"
elasticsearch:
  nodes:
    - url: "http://elasticsearch:9200"
  username: "elastic"
  password: "changeme"
  ssl_verification: false
rest :
  url: "http://fscrawler:8080"
```

## Known Issues

### Disk Space

Ensure that enough disk space is available. Even though I had 15 Gig of space available, the service failed, but this could have been a temporary issue. Just ensure enough space!

### Password

Don't spam random characters into the password. If you add a dollar sign, this gets interpreted as the starting character for a variable.
