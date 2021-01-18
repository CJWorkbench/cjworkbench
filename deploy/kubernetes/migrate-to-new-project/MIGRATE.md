How we migrate from one GCloud project to another
=================================================

These instructions were written and followed 2020-01-29.

1 - Set up the new cluster
--------------------------

Run `./cluster-setup.sh`.

Edit the variables at the top first. When it comes to secrets, consider
creating them all by hand (and commenting out the section of `cluster-setup.sh`
that creates them).

1. In the old kubectl context, `kubectl get secret [...] -oyaml >[...].yaml` for each secret.
1. Edit each secret, nixing the `namespace` and anything else other than `data`.
1. In the new kubectl context, `kubectl apply -f [...].yaml`.

2 - Move data
-------------

### 2a. Copy all data from old bucket to new, for each bucket.

[Create a service account](https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account):
```
gcloud iam service-accounts create storage-migrate
gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:storage-migrate@$PROJECT_ID.iam.gserviceaccount.com" --role "roles/owner"
gcloud iam service-accounts keys create GOOGLE_APPLICATION_CREDENTIALS.json --iam-account storage-migrate@$PROJECT_ID.iam.gserviceaccount.com
```

Give the *Storage Transfer Service* account access to the s3 buckets. (*NOT*
the `storage_migrate@...` service account!) [Find the account email](https://cloud.google.com/storage-transfer/docs/reference/rest/v1/googleServiceAccounts/get?apix_params=%7B%22projectId%22%3A%22workbench-staging%22%7D)
and then in Google Cloud Console "Storage Browser", shift-click all the
buckets; "Show Info Panel"; "Add Member"; copy/paste the storage transfer
account email; give it "Storage Object Viewer".

Give the same access in the *new* project.

Run our copying script:
```
GOOGLE_APPLICATION_CREDENTIALS=GOOGLE_APPLICATION_CREDENTIALS.json ./copy_buckets.py staging workbenchdata-staging.com
```

The script may prompt to enable the Storage Transfer API.

Finally, browse to each bucket and revoke the "Storage Transfer Service"
account's access.


### 2b. Migrate the database

Switch to the old project, and perform a database dump:

```
gcloud config configurations activate cjworkbench
kubectl config use-context gke_cj-workbench_us-central1-b_workbench
kubectl -n staging exec -it database-deployment-7d7c5457f6-4krl8 -- pg_dump -Ucjworkbench cjworkbench -Fc --quote-all-identifiers -f /to-migrate.psql
kubectl -n staging cp database-deployment-7d7c5457f6-4krl8:/to-migrate.psql ./to-migrate.psql
kubectl -n staging exec -it database-deployment-7d7c5457f6-4krl8 -- rm -f /to-migrate.psql
```

Switch to the new project and de-dump:

```
gcloud config configurations activate workbench-staging
kubectl config use-context gke_workbench-staging_us-central1-b_workbench
kubectl cp to-migrate.psql database-deployment-7d7c5457f6-4krl8:/
kubectl exec -it database-deployment-7d7c5457f6-4krl8 -- pg_restore -Ucjworkbench -dcjworkbench --no-owner /to-migrate.psql
kubectl exec -it database-deployment-7d7c5457f6-4krl8 -- rm /to-migrate.psql
```

When you're assured all is well, delete your copy. (This data is sensitive!)

```
rm to-migrate.psql
```
