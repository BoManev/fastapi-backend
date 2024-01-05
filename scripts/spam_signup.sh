#!/bin/bash

API_ENDPOINT="https://sitesync.me/api/contractor/signup"

while true; do
    RANDOM_STRING=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 10)
    RANDOM_PHONE_NUMBER=$((RANDOM%10000000000))
    RANDOM_EMAIL="${RANDOM_STRING}@sitesync.bg"

    FORM_DATA="email=${RANDOM_EMAIL}&first_name=bo&last_name=manev&phone_number=${RANDOM_PHONE_NUMBER}&password=test"
    curl -X POST -d "${FORM_DATA}" "${API_ENDPOINT}"
done