#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$bundle_dir"

if [[ ! -f image.tar || ! -f image.tar.sha256 || ! -f manifest.env ]]; then
  echo "closed deployment bundle is incomplete: image.tar, image.tar.sha256, and manifest.env are required" >&2
  exit 1
fi

bundle_format="$(sed -n 's/^BUNDLE_FORMAT=//p' manifest.env | head -n 1)"
image_ref="$(sed -n 's/^IMAGE_REF=//p' manifest.env | head -n 1)"
expected_image_id="$(sed -n 's/^IMAGE_ID=//p' manifest.env | head -n 1)"
source_revision="$(sed -n 's/^SOURCE_REVISION=//p' manifest.env | head -n 1)"

if [[ "$bundle_format" != "1" ]]; then
  echo "unsupported or missing BUNDLE_FORMAT in manifest.env" >&2
  exit 1
fi
if [[ -z "$image_ref" ]]; then
  echo "IMAGE_REF is required in manifest.env" >&2
  exit 1
fi
if [[ ! "$expected_image_id" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "IMAGE_ID in manifest.env must be a sha256 image ID" >&2
  exit 1
fi
if [[ ! "$source_revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_REVISION in manifest.env must be a 40-character lowercase git commit" >&2
  exit 1
fi

if ! command -v sha256sum >/dev/null 2>&1; then
  echo "sha256sum is required to verify the image archive" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to load the image archive" >&2
  exit 1
fi

if [[ "$(awk '$2 == "image.tar" { count += 1 } END { print count + 0 }' image.tar.sha256)" -ne 1 ]]; then
  echo "image.tar.sha256 must contain exactly one checksum entry for image.tar" >&2
  exit 1
fi

sha256sum --check image.tar.sha256
docker load --input image.tar

actual_image_id="$(docker image inspect --format '{{.Id}}' "$image_ref")"
if [[ "$actual_image_id" != "$expected_image_id" ]]; then
  echo "loaded image ID does not match manifest: expected $expected_image_id, got $actual_image_id" >&2
  exit 1
fi

echo "loaded image: $image_ref ($actual_image_id), source revision: $source_revision"
