from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


DEFAULT_JOB_ID = "trading-bot-daily-scan"


def load_json(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


def select_template_job(template_data: dict, job_id: str) -> dict:
	template_jobs = template_data.get("jobs")
	if not isinstance(template_jobs, list) or not template_jobs:
		raise ValueError("Template file must contain a non-empty 'jobs' list.")

	for job in template_jobs:
		if job.get("id") == job_id:
			return copy.deepcopy(job)

	raise ValueError(f"Template file does not contain job id '{job_id}'.")


def merge_job_definition(
	target_data: dict,
	template_job: dict,
	*,
	job_id: str,
	preserve_delivery_to: bool,
	append_if_missing: bool,
) -> tuple[dict, str]:
	jobs = target_data.get("jobs")
	if not isinstance(jobs, list):
		raise ValueError("Target file must contain a 'jobs' list.")

	merged = copy.deepcopy(target_data)
	merged_jobs = merged["jobs"]

	for index, existing_job in enumerate(merged_jobs):
		if existing_job.get("id") != job_id:
			continue

		replacement = copy.deepcopy(template_job)
		if preserve_delivery_to:
			existing_delivery_to = existing_job.get("delivery", {}).get("to")
			replacement_delivery = replacement.setdefault("delivery", {})
			if existing_delivery_to and replacement_delivery.get("to") in {None, "", "[REDACTED]"}:
				replacement_delivery["to"] = existing_delivery_to

		merged_jobs[index] = replacement
		return merged, "replaced"

	if not append_if_missing:
		raise ValueError(f"Target file does not contain job id '{job_id}'.")

	merged_jobs.append(copy.deepcopy(template_job))
	return merged, "appended"


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Safely merge the staged trading-bot OpenClaw cron job into a jobs.json file")
	parser.add_argument("--target", required=True, help="Path to the target OpenClaw jobs.json file.")
	parser.add_argument("--template", required=True, help="Path to the staged cron template JSON file.")
	parser.add_argument("--output", required=True, help="Path to write the merged candidate jobs.json file.")
	parser.add_argument("--job-id", default=DEFAULT_JOB_ID, help="Job id to replace inside the target file.")
	parser.add_argument(
		"--append-if-missing",
		action="store_true",
		help="Append the staged job if the target file does not already contain the configured job id.",
	)
	parser.add_argument(
		"--no-preserve-delivery-to",
		dest="preserve_delivery_to",
		action="store_false",
		help="Do not preserve the live delivery.to value when the staged template is redacted.",
	)
	parser.set_defaults(preserve_delivery_to=True)
	return parser


def main(argv: list[str] | None = None) -> None:
	parser = build_parser()
	args = parser.parse_args(argv)

	target_path = Path(args.target).expanduser().resolve()
	template_path = Path(args.template).expanduser().resolve()
	output_path = Path(args.output).expanduser().resolve()

	target_data = load_json(target_path)
	template_data = load_json(template_path)
	template_job = select_template_job(template_data, args.job_id)
	merged, action = merge_job_definition(
		target_data,
		template_job,
		job_id=args.job_id,
		preserve_delivery_to=args.preserve_delivery_to,
		append_if_missing=args.append_if_missing,
	)

	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

	print(json.dumps({
		"action": action,
		"job_id": args.job_id,
		"target": str(target_path),
		"template": str(template_path),
		"output": str(output_path),
		"preserved_delivery_to": args.preserve_delivery_to,
	}, indent=2))


if __name__ == "__main__":
	main()