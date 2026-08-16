PACKAGE := hm_2
VERSION := $(shell grep -oP '(?<=version = ")[^"]+' pyproject.toml | tr '.' '-')
CONTAINER := build/$(PACKAGE)-$(VERSION).sif

.PHONY: all clean sandbox

all: $(CONTAINER)

$(CONTAINER): Singularity.def
	mkdir -p build
	sudo singularity build $(CONTAINER) Singularity.def

# Optional: build a writable sandbox for faster iterative dev/testing
sandbox: Singularity.def
	mkdir -p build
	sudo singularity build --sandbox build/hm-$(PACKAGE)_sandbox/ Singularity.def

clean:
	rm -rf build