#!/usr/bin/env bash
echo $2
TEST_FILE=$1 TEST_NAME=$2 docker compose -f ./docker-compose-test.yaml up --build