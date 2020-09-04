FROM registry.fit2cloud.com/public/python:v3-sqlite
MAINTAINER Jumpserver Team <jiangjie.bai@fit2cloud.com>
ENV OMNIDB_VERSION=2.17.0

ARG PIP_MIRROR=https://pypi.douban.com/simple
ENV PIP_MIRROR=$PIP_MIRROR

WORKDIR /opt/omnidb

COPY . .
RUN useradd omnidb
RUN pip install -i ${PIP_MIRROR} --upgrade pip setuptools wheel
RUN pip install -i ${PIP_MIRROR} -r requirements.txt

VOLUME /opt/omnidb/data

ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

EXPOSE 8080
EXPOSE 25482

WORKDIR /opt/omnidb/OmniDB

#ENTRYPOINT ["python3", "omnidb-server.py", "-d", "/opt/omnidb/data"]
CMD ["python3", "omnidb-server.py", "-d", "/opt/omnidb/data"]
