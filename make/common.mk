SHELL := /bin/bash

# Load .env when available so both Make contexts reuse the same local settings.
ENV_FILE ?= .env
ENV_FILE_PATH := $(CURDIR)/$(ENV_FILE)
ifneq (,$(wildcard $(ENV_FILE_PATH)))
include $(ENV_FILE_PATH)
export
endif

SERVICE_PORT ?= 8000
