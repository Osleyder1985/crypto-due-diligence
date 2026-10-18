"""Single entry point for structural and semantic research-record validation."""
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from semantic_validation import validate_record_collection

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"
PIPELINE_VERSION = "1.0.0"


def load_schema():
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return schema


def validate_envelopes(envelopes, schema=None):
    """Validate all envelopes structurally first, then validate collection semantics.

    Semantic validation is skipped if any structural error exists, so malformed
    records cannot cause confusing secondary errors.
    """
    schema = schema or load_schema()
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    structural_errors = []
    for index, envelope in enumerate(envelopes):
        for error in validator.iter_errors(envelope):
            path = ".".join(str(part) for part in error.absolute_path) or "<root>"
            structural_errors.append(
                f"records[{index}].{path}: {error.message}"
            )
    if structural_errors:
        return {"valid": False, "stage": "structural", "errors": structural_errors}
    semantic_errors = validate_record_collection(envelopes)
    return {
        "valid": not semantic_errors,
        "stage": "semantic" if semantic_errors else "complete",
        "errors": semantic_errors,
    }


def validate_fixture(path, schema=None):
    with Path(path).open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    if not isinstance(fixture, dict) or not isinstance(fixture.get("records"), list):
        return {
            "valid": False,
            "stage": "fixture",
            "errors": ["fixture must be an object containing a records array"],
            "fixture": str(path),
        }
    result = validate_envelopes(fixture["records"], schema=schema)
    result["fixture"] = str(path)
    result["case_id"] = fixture.get("case_id")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    one = subparsers.add_parser("validate", help="validate one fixture or records JSON file")
    one.add_argument("path", type=Path)
    many = subparsers.add_parser("validate-fixtures", help="validate all JSON fixtures")
    many.add_argument("--directory", type=Path, default=ROOT / "fixtures" / "research")
    args = parser.parse_args(argv)
    schema = load_schema()

    if args.command == "validate":
        with args.path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        records = payload.get("records") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            result = {"valid": False, "stage": "input", "errors": ["input must be a records array or fixture object"]}
        else:
            result = validate_envelopes(records, schema=schema)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1

    paths = sorted(args.directory.glob("*.json"))
    if not paths:
        print(json.dumps({"valid": False, "errors": [f"no JSON fixtures found in {args.directory}"]}, indent=2))
        return 1
    results = [validate_fixture(path, schema=schema) for path in paths]
    output = {"pipeline_version": PIPELINE_VERSION, "valid": all(item["valid"] for item in results), "fixtures": results}
    print(json.dumps(output, indent=2))
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
