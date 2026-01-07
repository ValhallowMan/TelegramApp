#!/bin/bash
# migrate-code.sh
git pull origin main
docker compose down
docker compose up --build -d