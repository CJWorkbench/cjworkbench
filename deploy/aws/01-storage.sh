aws s3 mb s3://user-files.$DOMAIN_NAME
aws s3 mb s3://static.$DOMAIN_NAME
aws s3 mb s3://stored-objects.$DOMAIN_NAME
aws s3 mb s3://external-modules.$DOMAIN_NAME
aws s3 mb s3://cached-render-results.$DOMAIN_NAME
aws s3 mb s3://upload.$DOMAIN_NAME

# Uploads expire after 1d
echo '{"Rules":[{"Expiration":{"Days":1},"Prefix":"","Status":"Enabled","AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]}' \
  > 1d-lifecycle.json
aws s3api put-bucket-lifecycle-configuration \
  --bucket upload.$DOMAIN_NAME \
  --lifecycle-configuration file://$DIR/1d-lifecycle.json
rm -f 1d-lifecycle.json

# Static-files server
# Public-access...
aws s3api put-bucket-acl \
  --bucket static.$DOMAIN_NAME \
  --grant-read 'uri="http://acs.amazonaws.com/groups/global/AllUsers"'
# ... CORS...
aws s3api put-bucket-cors \
  --bucket static.$DOMAIN_NAME \
  --cors-configuration '{"CORSRules":[{"AllowedOrigins":["*"],"AllowedMethods":["GET","HEAD"]}]}'
# ... SSL...
aws acm request-certificate \
  --domain-name static.$DOMAIN_NAME \
  --validation-method DNS
static_cert_arn="$(aws acm list-certificates | jq -r ".CertificateSummaryList[] | select(.DomainName == \"static.$DOMAIN_NAME\") | .CertificateArn")"
echo "Go to https://console.aws.amazon.com/acm/home to generate the Route 53 record for '$static_cert_id' ('static.$DOMAIN_NAME') ... and then wait up to 30min...."
aws acm wait certificate-validated \
  --certificate-arn "$static_cert_arn"
# ... CDN...
read -r -d '' cloudfront_distribution_config <<EOT
  {
    "Comment": "static.$DOMAIN_NAME",
    "Enabled": true,
    "CallerReference": "static.$DOMAIN_NAME",
    "Aliases": {
      "Quantity": 1,
      "Items": ["static.$DOMAIN_NAME"]
    },
    "Origins": {
      "Quantity": 1,
      "Items": [
        {
          "Id": "static.$DOMAIN_NAME.s3.amazonaws.com",
          "DomainName": "static.$DOMAIN_NAME.s3.amazonaws.com",
          "OriginPath": "",
          "S3OriginConfig": { "OriginAccessIdentity": "" }
        }
      ]
    },
    "ViewerCertificate": {
      "ACMCertificateArn": "$static_cert_arn",
      "SSLSupportMethod": "sni-only"
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "static.$DOMAIN_NAME.s3.amazonaws.com",
      "ForwardedValues": {
        "QueryString": false,
        "Cookies": { "Forward": "none" },
        "Headers": { "Quantity": 0 },
        "QueryStringCacheKeys": { "Quantity": 0 }
      },
      "ViewerProtocolPolicy": "https-only",
      "MinTTL": 0,
      "DefaultTTL": 86400,
      "Compress": true
    }
  }
EOT
aws cloudfront create-distribution \
  --distribution-config "$cloudfront_distribution_config" \
  | jq  # avoid AWS's default pager
# ... DNS...
hosted_zone_id="$(aws route53 list-hosted-zones | jq -r ".HostedZones[] | select(.Name == \"$DOMAIN_NAME.\") | .Id")"
cloudfront_zone_id="Z2FDTNDATAQYW2"  # always, across all AWS
cloudfront_dns_name="$(aws cloudfront list-distributions | jq -r ".DistributionList.Items[] | select(.Origins.Items[0].DomainName == \"static.$DOMAIN_NAME.s3.amazonaws.com\") | .DomainName")"
read -r -d '' change_batch <<EOF
  {
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "static.$DOMAIN_NAME.",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "$cloudfront_zone_id",
            "DNSName": "$cloudfront_dns_name",
            "EvaluateTargetHealth": false
          }
        }
      },
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "static.$DOMAIN_NAME.",
          "Type": "AAAA",
          "AliasTarget": {
            "HostedZoneId": "$cloudfront_zone_id",
            "DNSName": "$cloudfront_dns_name",
            "EvaluateTargetHealth": false
          }
        }
      }
    ]
  }
EOF
aws route53 change-resource-record-sets \
  --hosted-zone-id "$hosted_zone_id" \
  --change-batch "$change_batch"

# Set up DNS
STATIC_IP=$(gcloud compute addresses describe user-files --global | grep address: | cut -b10-)
gcloud dns record-sets transaction start --zone=workbench-zone
gcloud dns record-sets transaction add --zone=workbench-zone --name user-files.$DOMAIN_NAME. --ttl 7200 --type A $STATIC_IP
gcloud dns record-sets transaction execute --zone=workbench-zone
