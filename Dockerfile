FROM python:2.7-onbuild
RUN cd /usr/src/app && python setup.py develop
WORKDIR /code
#ENTRYPOINT shipwright 
CMD shipwright