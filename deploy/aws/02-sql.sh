db_password="$(openssl rand -base64 20 | sed -e 's@/@-@')"

vpc_id="$(aws ec2 describe-vpcs --filter Name=tag:alpha.eksctl.io/cluster-name,Values=workbench | jq -r .Vpcs[0].VpcId)"
subnet1_az="$(aws ec2 describe-subnets --filter Name=vpc-id,Values=$vpc_id | jq -r '.Subnets[].AvailabilityZone' | sort -u | head -n1)"
subnet2_az="$(aws ec2 describe-subnets --filter Name=vpc-id,Values=$vpc_id | jq -r '.Subnets[].AvailabilityZone' | sort -u | tail -n1)"

aws ec2 create-subnet \
  --vpc-id "$vpc_id" \
  --cidr-block 192.168.254.0/24 \
  --availability-zone "$subnet1_az" \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=cjworkbench-role,Value=rds}]'
aws ec2 create-subnet \
  --vpc-id "$vpc_id" \
  --cidr-block 192.168.253.0/24 \
  --availability-zone "$subnet2_az" \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=cjworkbench-role,Value=rds}]'

subnet_ids_json_array="$(aws ec2 describe-subnets --filter Name=tag:cjworkbench-role,Values=rds | jq -c '[.Subnets[].SubnetId]')"
aws rds create-db-subnet-group \
  --db-subnet-group-name=cjworkbench \
  --db-subnet-group-description=cjworkbench \
  --subnet-ids "$subnet_ids_json_array"

# Workbench's DB requirements are rather small. Workbench only uses the DB for:
#
# * Users registration and authentication
# * "Document-editing" (Workbench "Workflows" are written in a JSON-like DSL.)
# * Locking
#
# Storage: 20GB (DB is tiny, let's hope we don't need high IOPS)
# t3.medium: 4GB is plenty
# Just one username/password: we can revisit auth later
# Private IP: this is our security mechanism
aws rds create-db-instance \
  --db-name cjworkbench \
  --db-instance-identifier cjworkbench \
  --db-instance-class db.t3.medium \
  --db-subnet-group-name cjworkbench \
  --allocated-storage 20 \
  --max-allocated-storage 200 \
  --engine postgres \
  --master-username cjworkbench \
  --master-user-password "$db_password" \
  --engine-version 13.2 \
  --auto-minor-version-upgrade \
  --no-publicly-accessible \
  --storage-encrypted

aws rds wait db-instance-available \
  --db-instance-id=cjworkbench

db_host="$(aws rds describe-db-instances --db-instance-identifier=cjworkbench | jq -r .DBInstances[].Endpoint.Address)"

kubectl create secret generic postgres-cjworkbench-credentials \
  --from-literal=host="$db_host" \
  --from-literal=username=cjworkbench \
  --from-literal=database=cjworkbench \
  --from-literal=password="$db_password"
