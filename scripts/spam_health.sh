#!/bin/bash

API_ENDPOINT="https://sitesync.me/api/health"

while true; do
    curl -s "$API_ENDPOINT"

    # sleep 1
done
