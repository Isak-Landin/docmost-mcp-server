#!/usr/bin/env bash

REMOTE="http://REMOTE_IP:4000/v1"

interpreter \
  --api_base "$REMOTE" \
  --model mistral-reason \
