FROM crazymax/7zip AS unzip
COPY models /opt/models
WORKDIR /opt/models
RUN 7z x -sdel final.7z.001
RUN 7z x -sdel HCLG.7z.001
RUN rm -r *7z*

FROM smartcommunitylab/cloud-asr-worker
MAINTAINER Ondrej Klejch

WORKDIR /opt/app
COPY --from=unzip /opt/models /opt/models
ADD config.py /opt/app/config.py

ENV MODEL nnet3-es
