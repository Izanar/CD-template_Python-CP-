#!/bin/bash -x
docker-compose pull && docker-compose down && docker-compose up -d
