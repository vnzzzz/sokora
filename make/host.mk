PORT ?= 8000
IMAGE_NAME ?= sokora
DEV_IMAGE_NAME ?= sokora-dev
VERSION ?=
VERSION_TAG := $(IMAGE_NAME):$(VERSION)
CONTAINER_NAME ?= sokora
DEV_CONTAINER_NAME ?= sokora-dev
DIST_DIR ?= dist
CLOSED_BUNDLE_DIR ?= $(DIST_DIR)/sokora-$(VERSION)-closed
NO_PROXY_VALUE := $(if $(NO_PROXY),$(NO_PROXY),$(no_proxy))
DOCKER_BUILD_PROXY_ARGS := $(if $(proxy),--build-arg http_proxy=$(proxy) --build-arg https_proxy=$(proxy) --build-arg HTTP_PROXY=$(proxy) --build-arg HTTPS_PROXY=$(proxy),) $(if $(NO_PROXY_VALUE),--build-arg no_proxy=$(NO_PROXY_VALUE) --build-arg NO_PROXY=$(NO_PROXY_VALUE),)
DOCKER_PROXY_ENV := $(if $(proxy),-e proxy=$(proxy) -e http_proxy=$(proxy) -e https_proxy=$(proxy) -e HTTP_PROXY=$(proxy) -e HTTPS_PROXY=$(proxy),) $(if $(NO_PROXY_VALUE),-e no_proxy=$(NO_PROXY_VALUE) -e NO_PROXY=$(NO_PROXY_VALUE),)
DOCKER_APPLICATION_ENV_VARS := SOKORA_LOG_LEVEL DATABASE_URL SOKORA_AUTH_SESSION_SECRET SOKORA_AUTH_ENABLED SOKORA_AUTH_SESSION_TTL_SECONDS SOKORA_AUTH_SESSION_HTTPS_ONLY SOKORA_LOCAL_AUTH_ENABLED SOKORA_LOCAL_ADMIN_USERNAME SOKORA_LOCAL_ADMIN_PASSWORD SOKORA_AUTH_CONFIG_ENCRYPTION_KEY OIDC_ISSUER OIDC_CLIENT_ID OIDC_CLIENT_SECRET OIDC_REDIRECT_URL OIDC_SCOPES OIDC_HTTP_TIMEOUT
DOCKER_APPLICATION_ENV_ARGS := $(foreach var,$(DOCKER_APPLICATION_ENV_VARS),-e $(var))

.PHONY: help build dev-build dev-shell require-version docker-build docker-run docker-stop closed-bundle package-closed-bundle

help:
	@printf "\nSokora Docker host targets:\n"
	@printf "  make build           Build unversioned production image (%s)\n" "$(IMAGE_NAME)"
	@printf "  make dev-build       Build the Dev Container Dockerfile image (%s)\n" "$(DEV_IMAGE_NAME)"
	@printf "  make dev-shell       Attach to the running devcontainer (name: %s)\n" "$(DEV_CONTAINER_NAME)"
	@printf "  make docker-build    Build versioned production image; requires VERSION\n"
	@printf "  make docker-run      Run versioned production image locally; requires VERSION\n"
	@printf "  make docker-stop     Stop and remove the production container\n"
	@printf "  make closed-bundle   Build and package versioned image; requires VERSION\n"
	@printf "  make package-closed-bundle SOURCE_REVISION=<sha>  Package an already-built versioned image; requires VERSION\n\n"

build:
	docker build $(DOCKER_BUILD_PROXY_ARGS) -t $(IMAGE_NAME) .

dev-build:
	docker build -f .devcontainer/Dockerfile -t $(DEV_IMAGE_NAME) .

dev-shell:
	docker exec -it $(DEV_CONTAINER_NAME) bash

require-version:
	@if [ -z "$(strip $(VERSION))" ]; then \
		echo "VERSION is required for versioned image/package targets; set VERSION=<version> or define it in .env" >&2; \
		exit 2; \
	fi

docker-build: require-version
	docker build $(DOCKER_BUILD_PROXY_ARGS) -t $(VERSION_TAG) .

docker-run: docker-build
	mkdir -p data
	docker run -d --name $(CONTAINER_NAME) $(DOCKER_APPLICATION_ENV_ARGS) $(DOCKER_PROXY_ENV) --rm \
		-e PORT="$(PORT)" \
		-p "$(SERVICE_PORT):$(PORT)" \
		-v $(abspath data):/app/data \
		$(VERSION_TAG)

docker-stop:
	-docker stop $(CONTAINER_NAME)

closed-bundle: docker-build
	SOURCE_REVISION="$$(git rev-parse HEAD)" bash ./scripts/deployment/package_closed_bundle.sh "$(VERSION_TAG)" "$(CLOSED_BUNDLE_DIR)"

package-closed-bundle: require-version
	@if [ -z "$(SOURCE_REVISION)" ]; then \
		echo "SOURCE_REVISION is required for an already-built image; set it to the commit used to build $(VERSION_TAG)" >&2; \
		exit 2; \
	fi
	SOURCE_REVISION="$(SOURCE_REVISION)" bash ./scripts/deployment/package_closed_bundle.sh "$(VERSION_TAG)" "$(CLOSED_BUNDLE_DIR)"
