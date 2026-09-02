#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$bundle_dir"

if [[ ! -f image.tar || ! -f image.tar.sha256 ]]; then
  echo "closed deployment bundle is incomplete: image.tar or image.tar.sha256 is missing" >&2
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

sha256sum --check image.tar.sha256
docker load --input image.tar

if [[ -f manifest.env ]]; then
  image_ref="$(sed -n 's/^IMAGE_REF=//p' manifest.env | head -n 1)"
  expected_image_id="$(sed -n 's/^IMAGE_ID=//p' manifest.env | head -n 1)"

  if [[ -n "$image_ref" && -n "$expected_image_id" ]]; then
    actual_image_id="$(docker image inspect --format '{{.Id}}' "$image_ref")"
    if [[ "$actual_image_id" != "$expected_image_id" ]]; then
      echo "loaded image ID does not match manifest: expected $expected_image_id, got $actual_image_id" >&2
      exit 1
    fi
    echo "loaded image: $image_ref ($actual_image_id)"
  elif [[ -n "$image_ref" ]]; then
    echo "loaded image: $image_ref"
  fi
fi
