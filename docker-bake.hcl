variable "PROJECT_ID" {
  default = "gcr.io/workbenchdata-ci"
}

variable "TAG" {
  default = "dev"
}

group "default" {
  targets = ["cron", "fetcher", "frontend", "migrate", "renderer", "tusd-hooks", "upload-assets"]
}

target "cron" {
  target = "cron"
  tags = ["gcr.io/${PROJECT_ID}/cron:${TAG}"]
}

target "fetcher" {
  target = "fetcher"
  tags = ["gcr.io/${PROJECT_ID}/fetcher:${TAG}"]
}

target "frontend" {
  target = "frontend"
  tags = ["gcr.io/${PROJECT_ID}/frontend:${TAG}"]
}

target "migrate" {
  target = "migrate"
  tags = ["gcr.io/${PROJECT_ID}/migrate:${TAG}"]
}

target "renderer" {
  target = "renderer"
  tags = ["gcr.io/${PROJECT_ID}/renderer:${TAG}"]
}

target "tusd-hooks" {
  target = "tusd-hooks"
  tags = ["gcr.io/${PROJECT_ID}/tusd-hooks:${TAG}"]
}

target "upload-assets" {
  target = "upload-assets"
  tags = ["gcr.io/${PROJECT_ID}/upload-assets:${TAG}"]
}

target "unittest" {
  target = "unittest"
  tags = ["gcr.io/${PROJECT_ID}/unittest:${TAG}"]
}

target "integration-test" {
  dockerfile = "Dockerfile.integration-test"
  target = "cloudbuild"
  tags = ["gcr.io/${PROJECT_ID}/integration-test:${TAG}"]
}
