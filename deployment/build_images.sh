export MODEL_URL=https://github.com/ffais/cloud-asr/blob/master/resources/model.zip?raw=true

docker build -t smartcommunitylab/cloud-asr-base:latest cloudasr/shared
docker build -t smartcommunitylab/cloud-asr-web:latest cloudasr/web
docker build -t smartcommunitylab/cloud-asr-api:latest cloudasr/api/
docker build -t smartcommunitylab/cloud-asr-worker:latest --build-arg MODEL_URL="${MODEL_URL}" cloudasr/worker/
docker build -t smartcommunitylab/cloud-asr-master:latest cloudasr/master/
docker build -t smartcommunitylab/cloud-asr-monitor:latest cloudasr/monitor/
docker build -t smartcommunitylab/cloud-asr-recordings:latest cloudasr/recordings/
docker build -t smartcommunitylab/cloud-asr-worker-it-small:latest examples/worker-it-small/
