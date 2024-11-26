# Build configuration
# -------------------

APP_NAME := `sed -n 's/^ *name.*=.*"\([^"]*\)".*/\1/p' pyproject.toml`
APP_VERSION := `sed -n 's/^ *version.*=.*"\([^"]*\)".*/\1/p' pyproject.toml`
GIT_REVISION = `git rev-parse HEAD`

# Introspection targets
# ---------------------

.PHONY: help
help: header targets

.PHONY: header
header:
	@echo "\033[34mEnvironment\033[0m"
	@echo "\033[34m---------------------------------------------------------------\033[0m"
	@printf "\033[33m%-23s\033[0m" "APP_NAME"
	@printf "\033[35m%s\033[0m" $(APP_NAME)
	@echo ""
	@printf "\033[33m%-23s\033[0m" "APP_VERSION"
	@printf "\033[35m%s\033[0m" $(APP_VERSION)
	@echo ""
	@printf "\033[33m%-23s\033[0m" "GIT_REVISION"
	@printf "\033[35m%s\033[0m" $(GIT_REVISION)
	@echo "\n"

.PHONY: targets
targets:
	@echo "\033[34mDevelopment Targets\033[0m"
	@echo "\033[34m---------------------------------------------------------------\033[0m"
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# Development targets
# -------------

.PHONY: install
install: ## Install dependencies
	poetry install

.PHONY: lock
lock: ## Update lock file
	poetry lock --no-update

.PHONY: run
run: start

.PHONY: start
start: ## Starts the server
	$(eval include .env)
	$(eval export $(sh sed 's/=.*//' .env))

	poetry run python main.py

# Misc targets
# ------------------------------

.PHONY: export
export: ## Export dependencies to requirements.txt
	poetry export -f requirements.txt --output requirements.txt

.PHONY: dependenciesLayer
dependenciesLayer: ## Package Lambda dependenciesLayer
	rm -rf dist/dependenciesLayer
	mkdir -p dist/dependenciesLayer/python/lib/python3.11/site-packages
	docker run --rm -v "$$(pwd)/dist/dependenciesLayer/python/lib/python3.11/site-packages":/var/task -v "$$(pwd)/requirements.txt":/requirements.txt "public.ecr.aws/sam/build-python3.11" /bin/sh -c "\
		pip install --platform manylinux2014_x86_64 \
		            --implementation cp \
		            --python-version 3.11 \
		            --only-binary=:all: \
		            -r /requirements.txt -t /var/task && \
		cd /var/task && zip -qr /var/task/dependenciesLayer.zip ."
	cd dist/dependenciesLayer && zip -r dependenciesLayer.zip python

.PHONY: sharedLayer
sharedLayer: ## Package Lambda sharedLayer
	rm -rf dist/sharedLayer
	mkdir -p dist/sharedLayer/python
	cp -r api dist/sharedLayer/python
	cp -r app dist/sharedLayer/python
	cp -r core dist/sharedLayer/python
	cd dist/sharedLayer && zip -r sharedLayer.zip python

.PHONY: backendLambda
backendLambda: ## Package Backend Lambda Code
	rm -rf dist/backendLambda
	mkdir -p dist/backendLambda
	cp main.py dist/backendLambda
	cd dist/backendLambda && zip -r backendLambda.zip .

.PHONY: processUploadedFiles
processUploadedFiles: ## Package Process Uploaded Files Lambda Code
	rm -rf dist/processUploadedFiles
	mkdir -p dist/processUploadedFiles
	cp lambdas/process_uploaded_files.py dist/processUploadedFiles
	cd dist/processUploadedFiles && zip -r processUploadedFiles.zip .

.PHONY: websocket_connect
websocket_connect: ## Package Websocket Connect For File Processing Lambda Code
	rm -rf dist/websocket_connect
	mkdir -p dist/websocket_connect
	cp lambdas/websocket_connect.py dist/websocket_connect
	cd dist/websocket_connect && zip -r websocket_connect.zip .

.PHONY: websocket_disconnect
websocket_disconnect: ## Package Websocket Disconnect For File Processing Lambda Code
	rm -rf dist/websocket_disconnect
	mkdir -p dist/websocket_disconnect
	cp lambdas/websocket_disconnect.py dist/websocket_disconnect
	cd dist/websocket_disconnect && zip -r websocket_disconnect.zip .

.PHONY: buildWithoutDependencies
buildWithoutDependencies: sharedLayer backendLambda processUploadedFiles websocket_connect websocket_disconnect

.PHONY: buildForLambda
buildForLambda: dependenciesLayer sharedLayer backendLambda processUploadedFiles websocket_connect websocket_disconnect

# Check, lint and format targets
# ------------------------------

.PHONY: check
check: check-format lint

.PHONY: check-format
check-format: ## Dry-run code formatter
	poetry run black ./ --check
	poetry run isort ./ --profile black --check

.PHONY: lint
lint: ## Run linter
	poetry run pylint ./api ./app ./core
 
.PHONY: format
format: ## Run code formatter
	poetry run black ./
	poetry run isort ./ --profile black

.PHONY: check-lockfile
check-lockfile: ## Compares lock file with pyproject.toml
	poetry lock --check

.PHONY: test
test: ## Run the test suite
	$(eval include .env)
	$(eval export $(sh sed 's/=.*//' .env))

	poetry run pytest -vv -s --cache-clear ./