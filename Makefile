SOKORA_MAKE_CONTEXT ?= host

include make/common.mk

ifeq ($(SOKORA_MAKE_CONTEXT),workspace)
include make/workspace.mk
else ifeq ($(SOKORA_MAKE_CONTEXT),host)
include make/host.mk
else
$(error SOKORA_MAKE_CONTEXT must be 'workspace' or 'host', got '$(SOKORA_MAKE_CONTEXT)')
endif
