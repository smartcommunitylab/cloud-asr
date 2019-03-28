FROM smartcommunitylab/cloud-asr-base

MAINTAINER Ondrej Klejch

RUN apt-get update && apt-get install -y libmysqlclient-dev
RUN pip install flask==0.10.1 flask-cors==2.1.2 flask-socketio==0.6.0 flask-sqlalchemy==2.1 MySQL-python==1.2.5 Werkzeug==0.9.6 gunicorn==19.1.1
RUN apt-get update && \
    apt-get install -y build-essential libatlas-base-dev python-dev python-pip git wget gfortran g++ unzip zlib1g-dev automake autoconf libtool subversion && \
    pip install webrtcvad && \
    pip install kafka-python
EXPOSE 80
ADD . /opt/app
WORKDIR /opt/app
CMD while true; do gunicorn -c gunicorn_config.py run:app; done
