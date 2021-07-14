variable "REPOSITORY" {
  default = "localhost"
}

variable "TAG" {
  default = "dev"
}

group "default" {
  targets = ["cron", "fetcher", "frontend", "migrate", "renderer", "tusd-hooks", "upload-assets"]
}

target "cron" {
  target = "cron"
  tags = ["${REPOSITORY}/cron:${TAG}"]
}

target "fetcher" {
  target = "fetcher"
  tags = ["${REPOSITORY}/fetcher:${TAG}"]
}

target "frontend" {
  target = "frontend"
  tags = ["${REPOSITORY}/frontend:${TAG}"]
}

target "migrate" {
  target = "migrate"
  tags = ["${REPOSITORY}/migrate:${TAG}"]
}

target "renderer" {
  target = "renderer"
  tags = ["${REPOSITORY}/renderer:${TAG}"]
}

target "tusd-hooks" {
  target = "tusd-hooks"
  tags = ["${REPOSITORY}/tusd-hooks:${TAG}"]
}

target "upload-assets" {
  target = "upload-assets"
  tags = ["${REPOSITORY}/upload-assets:${TAG}"]
}

target "unittest" {
  target = "unittest"
  tags = ["${REPOSITORY}/unittest:${TAG}"]
}

target "integration-test" {
  dockerfile = "Dockerfile.integration-test"
  target = "cloudbuild"
  tags = ["${REPOSITORY}/integration-test:${TAG}"]
}
