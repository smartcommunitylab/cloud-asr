CloudASR
========

CloudASR is a software platform and a public ASR webservice. Its three strong features are:
 - scalability
 - customizability
 - easy deployment

Platform’s API supports both batch and incremental speech recognition. The batch version is compatible with Google Speech API. New ASR engines can be added onto the platform and work simultaneously.

For more information have a look at [the documentation](http://www.cloudasr.com/documentation) or try out [our demo](http://www.cloudasr.com/demo).

## Contact us
The CloudASR platform is developed by the Dialogue Systems Group at [UFAL](http://ufal.mff.cuni.cz) and the work is funded by the Ministry of Education, Youth and Sports of the Czech Republic under the grant agreement LK11221, by the core research funding of Charles University in Prague. The language resources presented in this work are stored and distributed by the LINDAT/CLARIN project of the Ministry of Education, Youth and Sports of the Czech Republic (project LM2010013).

If you have any questions regarding CloudASR you can reach us at our mailinglist: [cloudasr@googlegroups.com](cloudasr@googlegroups.com).

SWARM
=====
## swarm configuration

### mysql secret example
echo "{dbrootpass}" | docker secret create mysql_root_password -

echo "{dbpass}" | docker secret create mysql_password -

echo "{mysql://{dbuser}:{dbpass}@{mysqlhost}:3306/{dbname}?charset=utf8}" | docker secret create connection_string -


K8S
===

## K8S configuration

### mysql secret example
kubectl create secret generic mysql-pass --from-literal=root_password='{dbrootpass}' --from-literal=password='{dbpass}'

### mysql configMap
kubectl create configmap mysql --from-file=deployment/script/schema.sql --from-file=resources/mysql_utf8.cnf

### connection string
kubectl create secret generic connection-string --from-literal=string='mysql://{dbuser}:{dbpass}@{mysqlhost}:3306/{dbname}?charset=utf8'


