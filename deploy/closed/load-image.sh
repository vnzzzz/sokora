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
  image_id="$(sed -n 's/^IMAGE_ID=//p' manifest.env | head -n 1)"
  [[ -n "$image_ref" ]] && echo "loaded image: $image_ref"
  [[ -n "$image_id" ]] && echo "expected image id: $image_id"
fi
