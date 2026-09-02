#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: package_closed_bundle.sh IMAGE_REF OUTPUT_DIR

Create a repository-free closed-network deployment bundle from an existing
production image. The bundle contains the Docker image archive, checksum,
Compose adapters, runtime templates, and operator instructions.
EOF
}

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

image_ref="$1"
output_dir="$2"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to package the production image" >&2
  exit 1
fi

if ! command -v sha256sum >/dev/null 2>&1; then
  echo "sha256sum is required to package the production image" >&2
  exit 1
fi

docker image inspect "$image_ref" >/dev/null

if [[ -L "$output_dir" ]]; then
  echo "refusing to replace symlink output directory: $output_dir" >&2
  exit 1
fi
if [[ -e "$output_dir" ]]; then
  if [[ ! -f "$output_dir/manifest.env" ]] || ! grep -Fxq 'BUNDLE_FORMAT=1' "$output_dir/manifest.env"; then
    echo "refusing to replace non-bundle output directory: $output_dir" >&2
    exit 1
  fi
  rm -rf -- "$output_dir"
fi
mkdir -p "$output_dir"

docker save --output "$output_dir/image.tar" "$image_ref"
(
  cd "$output_dir"
  sha256sum image.tar > image.tar.sha256
)

cp "$repo_root/deploy/closed/compose.sqlite.yaml" "$output_dir/compose.sqlite.yaml"
cp "$repo_root/deploy/closed/compose.postgresql.yaml" "$output_dir/compose.postgresql.yaml"
cp "$repo_root/deploy/closed/runtime.env.example" "$output_dir/runtime.env.example"
cp "$repo_root/deploy/closed/load-image.sh" "$output_dir/load-image.sh"
cp "$repo_root/deploy/closed/README.md" "$output_dir/README.md"
chmod +x "$output_dir/load-image.sh"

compose_env_template="$(<"$repo_root/deploy/closed/compose.env.example")"
printf '%s\n' "${compose_env_template//__SOKORA_IMAGE__/$image_ref}" > "$output_dir/compose.env.example"

image_id="$(docker image inspect --format '{{.Id}}' "$image_ref")"
source_revision="${SOURCE_REVISION:-}"
if [[ -z "$source_revision" ]] && command -v git >/dev/null 2>&1; then
  source_revision="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || true)"
fi
source_revision="${source_revision:-unknown}"

cat > "$output_dir/manifest.env" <<EOF
BUNDLE_FORMAT=1
IMAGE_REF=$image_ref
IMAGE_ID=$image_id
SOURCE_REVISION=$source_revision
EOF

printf 'closed deployment bundle created: %s\n' "$output_dir"
printf 'image: %s (%s)\n' "$image_ref" "$image_id"
