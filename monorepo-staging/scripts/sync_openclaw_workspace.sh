#!/usr/bin/env bash
set -euo pipefail

usage() {
	echo "Usage: $0 [--dry-run]" >&2
}

DRY_RUN=0
if [[ $# -gt 1 ]]; then
	usage
	exit 1
fi

if [[ $# -eq 1 ]]; then
	if [[ "$1" == "--dry-run" ]]; then
		DRY_RUN=1
	else
		usage
		exit 1
	fi
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/openclaw/workspace"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
DEST_DIR="$OPENCLAW_HOME/workspace"
SOURCE_SKILLS_DIR="$SOURCE_DIR/skills"
DEST_SKILLS_DIR="$DEST_DIR/skills"
SOURCE_EXTENSIONS_DIR="$SOURCE_DIR/.openclaw/extensions"
DEST_EXTENSIONS_DIR="$DEST_DIR/.openclaw/extensions"
FILES=(AGENTS.md BOOTSTRAP.md HEARTBEAT.md IDENTITY.md MIGRATION.md SOUL.md TOOLS.md USER.md)

mkdir -p "$DEST_DIR"

for file_name in "${FILES[@]}"; do
	if [[ ! -f "$SOURCE_DIR/$file_name" ]]; then
		echo "Missing staged workspace file: $SOURCE_DIR/$file_name" >&2
		exit 1
	fi

	if [[ "$DRY_RUN" -eq 1 ]]; then
		echo "Would sync $SOURCE_DIR/$file_name -> $DEST_DIR/$file_name"
		continue
	fi

	install -m 0644 "$SOURCE_DIR/$file_name" "$DEST_DIR/$file_name"
done

if [[ "$DRY_RUN" -eq 1 ]]; then
	echo "Dry run complete. ${#FILES[@]} OpenClaw workspace file(s) would sync to $DEST_DIR."
	if [[ -d "$SOURCE_SKILLS_DIR" ]]; then
		echo "Dry run complete. Workspace skill files under $SOURCE_SKILLS_DIR would sync to $DEST_SKILLS_DIR."
	fi
	if [[ -d "$SOURCE_EXTENSIONS_DIR" ]]; then
		echo "Dry run complete. Workspace extension files under $SOURCE_EXTENSIONS_DIR would sync to $DEST_EXTENSIONS_DIR."
	fi
	else
	if [[ -d "$SOURCE_SKILLS_DIR" ]]; then
		while IFS= read -r -d '' source_file; do
			relative_path="${source_file#"$SOURCE_SKILLS_DIR/"}"
			dest_file="$DEST_SKILLS_DIR/$relative_path"
			mkdir -p "$(dirname "$dest_file")"
			install -m 0644 "$source_file" "$dest_file"
		done < <(find "$SOURCE_SKILLS_DIR" -type f -print0)
	fi
	if [[ -d "$SOURCE_EXTENSIONS_DIR" ]]; then
		while IFS= read -r -d '' source_file; do
			relative_path="${source_file#"$SOURCE_EXTENSIONS_DIR/"}"
			dest_file="$DEST_EXTENSIONS_DIR/$relative_path"
			mkdir -p "$(dirname "$dest_file")"
			install -m 0644 "$source_file" "$dest_file"
		done < <(find "$SOURCE_EXTENSIONS_DIR" -type f -print0)
	fi
	echo "Synced ${#FILES[@]} OpenClaw workspace file(s) to $DEST_DIR."
fi