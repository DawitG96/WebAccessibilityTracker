.PHONY: up bump-version

up: bump-version
	docker compose up -d --build

bump-version:
	@./scripts/bump_version.sh
