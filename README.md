FDO to Ansible Automation Platform
===

This small API server is proxying ip address from a newly registered FDO device to Ansible Automation Platform.

Installation
---

```
$ make
$ make install
$ systemctl start fdo2ansible
```

The `make` command will just build a container image with fdo2ansible, while `make install` will deploy a systemd unit to run the container.

The configuration resides in `/etc/default/fdo2ansible`:

```
$ cat /etc/fdo2ansible
AWX_ENDPOINT=https://example-aap.apps.ansible-sno.redhat.com
AWX_TOKEN=<<<token>>>
```

The AWX token can be obtained by running `awx login` (this can be done using the container we built earlier).

Usage
---

This container is listening on port `5000` for a http call from the fdo registered devices, in the form: http://<fdo2ansible-server>:5000/<guid>/<ip>. The new device is supposed to be configured to run fdo2ansible via serviceinfo api:

```
...
  - command: /bin/bash
    args:
    - -c
    - 'curl http://192.168.122.253:5000/device/$(fdo-owner-tool dump-device-credential /etc/device-credentials | grep GUID | cut -d: -f2 | xargs)/$(hostname -i)'
...
```

When it receives a guid that's known and and existing in Ansible, fdo2ansible will create a new host with the received ip as the `andible_host` variable. At this point, if Ansible Automation Platform has the correct ssh key, the host is configurable via any Ansible manifest.