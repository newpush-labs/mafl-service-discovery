DOCKER_REPO := lracz/mafl-service-discovery
VERSION := 1.0.2

.PHONY: build
build:
	docker buildx create --use --name mafl-service-discovery-builder
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(DOCKER_REPO):$(VERSION) \
		-t $(DOCKER_REPO):latest \
		--push .

.PHONY: push
push:
	docker push $(DOCKER_REPO):$(VERSION)
	docker push $(DOCKER_REPO):latest

.PHONY: clean
clean:
	docker buildx rm mafl-service-discovery-builder

.PHONY: all
all: build push clean
