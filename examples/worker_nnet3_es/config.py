basedir = '/opt/models'
wst_path = '%s/words.txt' % basedir
kaldi_config = [
    '--endpoint.silence-phones="1:2:3:4:5"'
    '--mfcc-config=%s/mfcc_hires.conf' % basedir,
    '--ivector-extraction-config=%s/ivector_extractor.conf' % basedir,
    '--frame-subsampling-factor=3',
    '--frames-per-chunk=140',
    '--extra-left-context-initial=0',
    '--frame-subsampling-factor=3',
    '--min-active=200',
    '--max-active=7000',
    '--beam=15.0',
    '--lattice-beam=6.0',
    '--acoustic-scale=1.0',
    '--minimize=false',
    '--port-num=5050',
    '%s/final.mdl' % basedir,
    '%s/HCLG.fst' % basedir,
    '%s/words.txt' % basedir
]
