#!/usr/bin/env python3
"""
Language coverage analysis script.

Analyzes translation coverage by comparing each language against English.
Lists available languages and shows what percentage of each language is fully covered.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml


def eq_sep(n: int = 70):
    print("=" * n)


def line_sep(n: int = 70):
    print("-" * n)


def get_localization_dir() -> Path:
    """Get the localization directory path."""
    project_root = Path(__file__).parent.parent
    return project_root / "source" / "resources" / "localization"


def all_keys_from_dict_recursive(d: dict, prefix="") -> set[str]:
    """Recursively extract all keys from a nested dictionary."""
    keys = set()
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(all_keys_from_dict_recursive(value, full_key))
    return keys


def get_value_from_dict(d: dict, key_path: str):
    """Get a value from nested dictionary using dot notation."""
    keys = key_path.split(".")

    value = d
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def is_key_covered(d, key_path):
    """Check if a key exists and has a non-empty value."""
    value = get_value_from_dict(d, key_path)
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    return True


def load_yaml_file(filepath: Path):
    """Load a YAML file and return its content."""
    try:
        with filepath.open(encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content if content is not None else {}
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return {}


def keys_from_yaml(pth: Path):
    return all_keys_from_dict_recursive(load_yaml_file(pth))


def keys_from_categories(lst: list[tuple[str, Path]]):
    for category, filepath in sorted(lst):
        keys = keys_from_yaml(filepath)
        yield (category, keys)


def get_language_files(directory: Path) -> dict[str, list[tuple[str, Path]]]:
    language_files = defaultdict(list)
    for filepath in sorted(localization_dir.glob("*.yml")):
        filename = filepath.name
        parts = filename.rsplit(".", 2)  # Split into [category, lang, yml]
        if len(parts) == 3:
            category, lang, _ = parts
            language_files[lang].append((category, filepath))
    return language_files


def analyze_coverage(localization_dir: Path, list_missing_keys=False, language=None) -> int:
    """Analyze language coverage for all available languages.

    Args:
        localization_dir: Path to the localization directory
        list_missing_keys: If True, print detailed missing keys by language.
        language: If provided, only analyze this specific language.
    """

    # Discover all language files
    language_files: dict[str, list[tuple[str, Path]]] = get_language_files(localization_dir)

    if "en" not in language_files:
        print("Error: English (en) translations not found!")
        return 1

    eq_sep()
    print("LANGUAGE COVERAGE ANALYSIS")
    eq_sep()
    print()
    print("English (Reference):")
    line_sep()

    # Get all English keys
    english_keys_per_category = {}
    total_english_keys = 0
    for category, keys in keys_from_categories(language_files["en"]):
        if not keys:
            print(f"  {category:<20}     0 keys, skipping...")
        english_keys_per_category[category] = keys
        total_english_keys += len(keys)
        print(f"  {category:<20} {len(keys):>5} keys")

    print(f"  {'TOTAL':<20} {total_english_keys:>5} keys")
    print()

    if language:
        # Filter to specific language if requested
        if language.lower() not in language_files:
            print(f"Error: Language '{language}' not found.")
            print(f"Available languages: {', '.join(sorted(language_files.keys()))}")
            return 1
        languages = [language.lower()]
        # Automatically show missing keys in single-language mode
        list_missing_keys = True
    else:
        # Analyze other languages
        languages = sorted(lang for lang in language_files if lang != "en")

    coverage_data = []
    missing_keys_by_lang = {}

    for lang in languages:
        print(f"{lang.upper()} Translation:")
        line_sep()

        covered_keys = 0
        total_keys = total_english_keys
        missing_keys_by_lang[lang] = defaultdict(list)

        for category, filepath in sorted(language_files["en"]):
            if lang not in language_files or not any(c == category for c, _ in language_files[lang]):
                # Language file missing for this category
                category_keys = len(english_keys_per_category[category])
                print(f"  {category:<20} {'MISSING':<20} (0/{category_keys})")
                # Add all keys as missing for this category
                missing_keys_by_lang[lang][category].extend(sorted(english_keys_per_category[category]))
                continue

            # Load the language file
            lang_filepath = filepath.parent / f"{category}.{lang}.yml"
            lang_content = load_yaml_file(lang_filepath)

            # Count covered keys and track missing ones
            category_covered = 0
            for key in english_keys_per_category[category]:
                if is_key_covered(lang_content, key):
                    category_covered += 1
                else:
                    missing_keys_by_lang[lang][category].append(key)

            category_total = len(english_keys_per_category[category])
            covered_keys += category_covered

            coverage_ratio = category_covered / category_total
            print(f"  {category:<20} {coverage_ratio * 100:>6.1f}% ({category_covered}/{category_total})")

        coverage_ratio = covered_keys / total_keys
        print(f"  {'TOTAL':<20} {coverage_ratio * 100:>6.1f}% ({covered_keys}/{total_keys})")
        print()

        coverage_data.append((lang, coverage_ratio, covered_keys, total_keys))

    # Summary table
    eq_sep()
    print("COVERAGE SUMMARY")
    eq_sep()
    print(f"{'Language':<15} {'Coverage':<15} {'Keys':<20}")
    line_sep()

    coverage_data.sort(key=lambda x: x[1], reverse=True)
    for lang, coverage_ratio, covered, total in coverage_data:
        print(f"{lang.upper():<15} {coverage_ratio * 100:>6.1f}% {covered:>6}/{total:<6}")

    eq_sep()
    print()

    # Missing keys section (optional)
    if list_missing_keys:
        eq_sep()
        print("MISSING KEYS BY LANGUAGE")
        eq_sep()

        for lang, _, covered, total in sorted(coverage_data, key=lambda x: x[2] / x[3] if x[2] != x[3] else 0):
            missing_count = total - covered
            if missing_count == 0:
                print(f"\n{lang.upper()}: ✓ All keys translated ({covered}/{total})")
                continue

            print(f"\n{lang.upper()}: {missing_count} missing key(s)")
            line_sep()
            for category in sorted(missing_keys_by_lang[lang].keys()):
                missing = missing_keys_by_lang[lang][category]
                if missing:
                    print(f"  {category}:")
                    for key in sorted(missing):
                        print(f"    • {key}")

        eq_sep()

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze language coverage for translations.")
    parser.add_argument(
        "--list-missing-keys",
        action="store_true",
        help="List all missing keys by language.",
    )
    parser.add_argument(
        "--language",
        type=str,
        help="Check progress for a specific language (automatically shows missing keys).",
    )
    args = parser.parse_args()

    localization_dir = get_localization_dir()

    if not localization_dir.exists():
        print(f"Error: Localization directory not found: {localization_dir}")
        sys.exit(1)

    sys.exit(
        analyze_coverage(
            localization_dir,
            list_missing_keys=args.list_missing_keys,
            language=args.language,
        )
    )
