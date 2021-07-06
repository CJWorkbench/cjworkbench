variable "TAG" {
  default = "dev"
}

group "default" {
  targets = ["cron", "fetcher", "frontend", "migrate", "renderer", "tusd-hooks", "upload-assets"]
}

target "cron" {
  target = "cron"
  tags = ["gcr.io/workbenchdata-ci/cron:${TAG}"]
}

target "fetcher" {
  target = "fetcher"
  tags = ["gcr.io/workbenchdata-ci/fetcher:${TAG}"]
}

target "frontend" {
  target = "frontend"
  tags = ["gcr.io/workbenchdata-ci/frontend:${TAG}"]
}

target "migrate" {
  target = "migrate"
  tags = ["gcr.io/workbenchdata-ci/migrate:${TAG}"]
}

target "renderer" {
  target = "renderer"
  tags = ["gcr.io/workbenchdata-ci/renderer:${TAG}"]
}

target "tusd-hooks" {
  target = "tusd-hooks"
  tags = ["gcr.io/workbenchdata-ci/tusd-hooks:${TAG}"]
}

target "upload-assets" {
  target = "upload-assets"
  tags = ["gcr.io/workbenchdata-ci/upload-assets:${TAG}"]
}
