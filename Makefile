SHELL := bash
podman=podman
image=fdo2ansible

default: build

build:
	$(podman) build . --tag $(image)
install:
	cp fdo2ansible.service /etc/systemd/system/fdo2ansible.service
	systemctl daemon-reload
uninstall:
	systemctl stop fdo2ansible.service
	rm /etc/systemd/system/fdo2ansible.service
	systemctl daemon-reload