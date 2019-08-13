# Example for python 3.5
# make publish-py35 PROFILE=default
# aws ecr list-images --repository-name buzzard
# open https://circleci.com/gh/airware/buzzard/edit#env-vars

PROFILE := dev
REGION := us-east-1
NAME := $(shell (aws ecr describe-repositories --region ${REGION} --profile ${PROFILE} || echo "{\"repositories\":[{\"repositoryName\":\"buzzard\", \"repositoryUri\":\"local-repository\"}]}") | jq -r ".repositories[] | select ( .repositoryName == \"buzzard\") | .repositoryUri")
VERSION := $(shell echo `date "+%Y%m%d"`)
ECR_AUTH := $(shell aws --region ${REGION} ecr get-login --profile ${PROFILE} --no-include-email)
PY27_VERSION := 2.7.15
PY35_VERSION := 3.5.7
PY36_VERSION := 3.6.6
PY37_VERSION := 3.7.0

.PHONY: clean build-py37 build-py36 build-py35 build-py27 publish

all: publish

clean:
	@echo "--> Cleaning up untagged images"
	$(eval dangling := $(shell docker images -f dangling=true -q))
	-docker rmi $(dangling)

build-py27:
	@echo "--> Building docker image"
	mkdir -p build
	docker build -f Dockerfile \
				 -t ${NAME}:${PY27_VERSION}-${VERSION} \
				 --build-arg PYTHON_VERSION=${PY27_VERSION} \
				 .
	@echo built ${NAME}:${PY27_VERSION}-${VERSION}
	@printf ${NAME}:${PY27_VERSION}-${VERSION} > ./build/tagname-${PY27_VERSION}

build-py35:
	@echo "--> Building docker image"
	mkdir -p build
	docker build -f Dockerfile \
				 -t ${NAME}:${PY35_VERSION}-${VERSION} \
				 --build-arg PYTHON_VERSION=${PY35_VERSION} \
				 .
	@echo built ${NAME}:${PY35_VERSION}-${VERSION}
	@printf ${NAME}:${PY35_VERSION}-${VERSION} > ./build/tagname-${PY35_VERSION}

build-py36:
	@echo "--> Building docker image"
	mkdir -p build
	docker build -f Dockerfile \
				 -t ${NAME}:${PY36_VERSION}-${VERSION} \
				 --build-arg PYTHON_VERSION=${PY36_VERSION} \
				 .
	@echo built ${NAME}:${PY36_VERSION}-${VERSION}
	@printf ${NAME}:${PY36_VERSION}-${VERSION} > ./build/tagname-${PY36_VERSION}

build-py37:
	@echo "--> Building docker image"
	mkdir -p build
	docker build -f Dockerfile \
				 -t ${NAME}:${PY37_VERSION}-${VERSION} \
				 --build-arg PYTHON_VERSION=${PY37_VERSION} \
				 .
	@echo built ${NAME}:${PY37_VERSION}-${VERSION}
	@printf ${NAME}:${PY37_VERSION}-${VERSION} > ./build/tagname-${PY37_VERSION}

publish-py27: build-py27
	@echo "--> Authentication on AWS ECR"
	${ECR_AUTH}
	docker push $(shell cat ./build/tagname-${PY27_VERSION})

publish-py35: build-py35
	@echo "--> Authentication on AWS ECR"
	${ECR_AUTH}
	docker push $(shell cat ./build/tagname-${PY35_VERSION})

publish-py36: build-py36
	@echo "--> Authentication on AWS ECR"
	${ECR_AUTH}
	docker push $(shell cat ./build/tagname-${PY36_VERSION})

publish-py37: build-py37
	@echo "--> Authentication on AWS ECR"
	${ECR_AUTH}
	docker push $(shell cat ./build/tagname-${PY37_VERSION})

publish: publish-py27 publish-py35 publish-py36 publish-py37
