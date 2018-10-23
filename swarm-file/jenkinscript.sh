#!/bin/bash
cd swarm-file
files="*.yaml"
regex="(worker-)([a-z-]+).yaml"
for f in $files
do
    if [[ $f =~ $regex ]]
    then
        mod="${BASH_REMATCH[2]}"
        worker="worker-$mod"        
        ssh -i /var/jenkins_home/azure -o "StrictHostKeyChecking no" dev@$ip "az vm show --name $worker --resource-group cloud-asr-swarm -o table"
        if [ $? -eq 0 ]        
        then
          echo "VM exist" 
        else
          echo "VM non found"
          vmsize=$(sed -r -n 's/.+size:\s+\"([a-zA-Z0-9_\-]+)\"/\1/p' $f)
          ssh -i /var/jenkins_home/azure -o "StrictHostKeyChecking no" dev@$ip  "az vm create --resource-group cloud-asr-swarm --name $worker --location westeurope --size $vmsize --admin-username
          dev --ssh-key-value @/home/dev/azure.pub --storage-sku Standard_LRS --vnet-name cloud-asr-swarm-vnet --subnet default --public-ip-address \"\" --tags model=$worker --image Canonical:UbuntuServer:18.04-LTS:latest --custom-data /home/dev/cloud-init.txt"
	
	      until [[ $(ssh -i /var/jenkins_home/azure dev@$ip docker node ls --format "{{.Hostname}}" --filter name=$worker) = $worker ]]; do
            echo "waiting 1m"
            sleep 1m
          done
	      echo "Joined as worker"
          ssh -i /var/jenkins_home/azure dev@$ip 'cd ~/cloud-asr; git pull origin secret'
          ssh -i /var/jenkins_home/azure dev@$ip docker node update --label-add model=$mod $worker
          workerfile="$worker.yaml"
          ssh -i /var/jenkins_home/azure dev@$ip "cd ~/cloud-asr/swarm-file; docker stack deploy -c $workerfile $worker"
        fi 
    fi
done
