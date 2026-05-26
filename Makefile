IMAGE_NAME=findthatproduct

.PHONY: build test clean

build:
	docker build -t $(IMAGE_NAME) .

test:
	make build
	docker run --rm $(IMAGE_NAME)

clean:
	docker rmi $(IMAGE_NAME) || true

