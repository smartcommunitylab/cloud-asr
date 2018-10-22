#!/bin/bash
cd swarm-file
VMLIST=( $(az vm list --query "[].name" -o tsv) )
regex="(worker-)([a-z-]+)"
for VM in "${VMLIST[@]}"
do
  if [[ $VM =~ $regex ]]
  then
    vmfile="$VM.yaml"
    echo "check if file exist"
    found="0"
    files="*.yaml"
    for f in $files
    do
      if [ "$f" == "$vmfile" ] ; then
        found="1"
      fi
    done  
    if [ "$found" == "0" ]; then
      az resource delete --id $(az resource list --tag model=$VM --query "[].id" -otsv)
    fi
  else
    echo "is not a worker"
  fi
done

