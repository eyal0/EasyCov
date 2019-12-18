# Container image that runs your code
FROM alpine

RUN apk --update add git wget python py-pip
RUN pip install coverage
RUN pip install wheel
RUN pip install colorama

COPY . /root/EasyCov/
RUN pip install /root/EasyCov
RUN hash -r

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python", "/root/EasyCov/action.py"]
