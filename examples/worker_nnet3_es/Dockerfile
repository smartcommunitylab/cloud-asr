FROM crazymax/7zip AS unzip
COPY models /model
WORKDIR /model
RUN 7z x -sdel final.7z.001
RUN 7z x -sdel HCLG.7z.001
RUN rm -r *7z*

FROM smartcommunitylab/kaldi-online-tcp
COPY --from=unzip /model /model
WORKDIR /model
ENTRYPOINT ["online2-tcp-nnet3-decode-faster",\
"--endpoint.silence-phones=1:2:3:4:5",\
"--mfcc-config=mfcc_hires.conf",\
"--ivector-extraction-config=ivector_extractor.conf",\
"--frame-subsampling-factor=3",\
"--frames-per-chunk=140",\
"--extra-left-context-initial=0",\
"--min-active=200",\
"--max-active=7000",\
"--beam=15",\
"--lattice-beam=6.0",\
"--acoustic-scale=1.0",\
"--minimize=false",\
"--port-num=5050","final.mdl","HCLG.fst","words.txt"]

ENV MODEL nnet3-es
