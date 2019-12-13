# Container image that runs your code
FROM ubuntu:16.04

COPY * /root/EasyCov

RUN apt-get update
RUN apt-get -y install python
RUN apt-get -y install python-pip
RUN apt-get -y install python-pip-whl
RUN apt-get -y install git
RUN pip install coverage
RUN pip install wheel
RUN cd /root/EasyCov
RUN pip install .
RUN hash -r

RUN mkdir -p /tmp/push

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python", "/root/action.py"]
