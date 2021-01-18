#!/usr/bin/env python3

# [2020-01-29] copied from https://raw.githubusercontent.com/GoogleCloudPlatform/python-docs-samples/master/storage/transfer_service/nearline_request.py
#
# Transfers all data *from* our s3 buckets at
# $ENV-xxx.workbenchdata.com, *to* our s3 buckets at
# xxx.$DOMAIN.
#
# Copyright 2015, Google, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import datetime
import json

import googleapiclient.discovery

BUCKETS = [
    "user-files",
    "static",
    "stored-objects",
    "external-modules",
    "cached-render-results",
]


def main(env, domain):
    storagetransfer = googleapiclient.discovery.build("storagetransfer", "v1")

    project_id = "workbench-" + env

    for bucket in BUCKETS:
        source_bucket = f"{env}-{bucket}.workbenchdata.com"
        sink_bucket = f"{bucket}.{domain}"
        description = "Copy everything from gs://{source_bucket} to gs://{sink_bucket}"

        transfer_job = {
            "description": description,
            "status": "ENABLED",
            "projectId": project_id,
            "schedule": {"scheduleStartDate": {"year": 2000, "month": 1, "day": 1}},
            "transferSpec": {
                "gcsDataSource": {"bucketName": source_bucket},
                "gcsDataSink": {"bucketName": sink_bucket},
                "transferOptions": {"deleteObjectsFromSourceAfterTransfer": False},
            },
        }

        result = storagetransfer.transferJobs().create(body=transfer_job).execute()
        print("transferJob: {}".format(json.dumps(result, indent=4)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("env", help="Environment ('staging' or 'production')")
    parser.add_argument(
        "domain", help="Domain of new bucket (e.g., 'workbenchdata-staging.com')"
    )

    args = parser.parse_args()

    main(args.env, args.domain)
