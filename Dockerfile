# Container image that runs your code
FROM ubuntu:16.04

RUN apt-get update
RUN apt-get -y install wget
RUN apt-get -y install make libssl-dev libghc-zlib-dev libcurl4-gnutls-dev libexpat1-dev gettext unzip
# Use a newer version of git so that we can fetch commits by SHA.
RUN cd /root && wget https://github.com/git/git/archive/v2.24.1.tar.gz && tar xzvf v2.24.1.tar.gz && cd git-2.24.1 && make prefix=/usr/local all && make prefix=/usr/local install && hash -r
RUN apt-get -y install python
RUN apt-get -y install python-pip
RUN apt-get -y install python-pip-whl
RUN pip install coverage
RUN pip install wheel
RUN pip install colorama

COPY . /root/EasyCov/
RUN pip install /root/EasyCov
RUN hash -r

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python", "/root/EasyCov/action.py"]
