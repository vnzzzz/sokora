#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: SOURCE_REVISION=<40-char git commit> package_closed_bundle.sh IMAGE_REF OUTPUT_DIR

Create a repository-free closed-network deployment bundle from an existing
production image. SOURCE_REVISION must identify the source commit used to
build that image; it is never inferred from the packaging checkout.
EOF
}

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

image_ref="$1"
output_dir="$2"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_revision="${SOURCE_REVISION:-}"

if [[ ! "$source_revision" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "SOURCE_REVISION is required and must be the 40-character git commit used to build the packaged image" >&2
  exit 2
fi

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
fi

output_parent="$(dirname "$output_dir")"
output_name="$(basename "$output_dir")"
mkdir -p "$output_parent"
temp_dir="$(mktemp -d "$output_parent/.${output_name}.tmp.XXXXXX")"
backup_dir=""

cleanup() {
  status=$?
  trap - EXIT
  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf -- "$temp_dir"
  fi
  if [[ -n "$backup_dir" && -e "$backup_dir" && ! -e "$output_dir" ]]; then
    mv -- "$backup_dir" "$output_dir" || true
  fi
  exit "$status"
}
trap cleanup EXIT

docker save --output "$temp_dir/image.tar" "$image_ref"
(
  cd "$temp_dir"
  sha256sum image.tar > image.tar.sha256
)

cp "$repo_root/deploy/closed/compose.sqlite.yaml" "$temp_dir/compose.sqlite.yaml"
cp "$repo_root/deploy/closed/compose.postgresql.yaml" "$temp_dir/compose.postgresql.yaml"
cp "$repo_root/deploy/closed/runtime.env.example" "$temp_dir/runtime.env.example"
cp "$repo_root/deploy/closed/load-image.sh" "$temp_dir/load-image.sh"
cp "$repo_root/deploy/closed/README.md" "$temp_dir/README.md"
chmod +x "$temp_dir/load-image.sh"

compose_env_template="$(<"$repo_root/deploy/closed/compose.env.example")"
printf '%s\n' "${compose_env_template//__SOKORA_IMAGE__/$image_ref}" > "$temp_dir/compose.env.example"

image_id="$(docker image inspect --format '{{.Id}}' "$image_ref")"
source_revision="${source_revision,,}"

# Write the manifest last so only a complete staging directory can ever be
# recognized as a replaceable bundle on a later invocation.
cat > "$temp_dir/manifest.env" <<EOF
BUNDLE_FORMAT=1
IMAGE_REF=$image_ref
IMAGE_ID=$image_id
SOURCE_REVISION=$source_revision
EOF

if [[ -e "$output_dir" ]]; then
  backup_dir="$(mktemp -d "$output_parent/.${output_name}.previous.XXXXXX")"
  rmdir "$backup_dir"
  mv -- "$output_dir" "$backup_dir"
fi

# temp_dir and output_dir share a parent, so this rename stays on one
# filesystem. If it fails after moving the old bundle aside, the EXIT trap
# restores the previous known-good directory.
mv -- "$temp_dir" "$output_dir"
temp_dir=""

if [[ -n "$backup_dir" ]]; then
  rm -rf -- "$backup_dir"
  backup_dir=""
fi
trap - EXIT

printf 'closed deployment bundle created: %s\n' "$output_dir"
printf 'image: %s (%s), source revision: %s\n' "$image_ref" "$image_id" "$source_revision"
