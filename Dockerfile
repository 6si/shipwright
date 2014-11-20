FROM python:2.7-onbuild
RUN cd /usr/src/app && python setup.py install
WORKDIR /code
CMD /usr/local/bin/shipwright