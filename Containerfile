FROM quay.io/centos/centos:stream8
RUN dnf install -y python3-pip python3-flask fdo-owner-cli
RUN pip3 install awxkit ConfigArgParse
ADD fdo2ansible.py /usr/bin/fdo2ansible
RUN chmod +x /usr/bin/fdo2ansible