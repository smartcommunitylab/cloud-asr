#!/bin/bash

files="*.yaml"
regex="(worker-)([a-z-]+).yaml"
for f in $files
do
    if [[ $f =~ $regex ]]
    then
        mod="${BASH_REMATCH[2]}"
        worker="worker-$mod"        
        az vm show --name $worker --resource-group cloud-asr-swarm -o table
        if [ $? -eq 0 ]        
        then
          echo "VM exist" 
          vmsize=$(sed -r -n 's/.+-\s+size:\s+\"([a-zA-Z0-9_\-]+)\"/\1/p' $f)
          echo $vmsize
        else
          echo "VM non found"
          
          az vm create --resource-group cloud-asr-swarm --name $worker --location westeurope --size Standard_B2ms \
          --admin-username dev --ssh-key-value @~/Documenti/azure.pub --storage-sku Standard_LRS --vnet-name cloud-asr-swarm-vnet \
          --subnet default --public-ip-address """" --image Canonical:UbuntuServer:18.04-LTS:latest --custom-data cloud-init.txt
	
	        ip=$(az vm list-ip-addresses --resource-group cloud-asr-swarm --name $worker --query [0].virtualMachine.network.privateIpAddresses[0] -o tsv) 
	
	        until [[ $(ssh -i ~/Documenti/azure dev@23.97.228.138 docker node ls --format "{{.Hostname}}" --filter name=$worker) = $worker ]]; do
            echo "waiting 1m"
            sleep 1m
          done
	        echo "Joined as worker"
          ssh -i ~/Documenti/azure dev@23.97.228.138 'cd ~/cloud-asr; git pull origin secret'
          ssh -i ~/Documenti/azure dev@23.97.228.138 docker node update --label-add model=$mod $worker
          workerfile="$worker.yaml"
          ssh -i ~/Documenti/azure dev@23.97.228.138 "cd ~/cloud-asr/swarm-file; docker stack deploy -c $workerfile $worker"
        fi 
    fi
done
