dart_tool_cache="$toolkit/.pub-cache"
dart_tools="$dart_tool_cache/bin"
dart_binary=$(command -v dart || true)

require_resolved_dart_package() {
    if [ ! -f "$1/.dart_tool/package_config.json" ]; then
        echo "checks: $1 has no .dart_tool - run dart pub get there" >&2
        exit 1
    fi
}

require_strict_dart_rules() {
    strict_rules_package=package:very_good_analysis/

    if ! grep -qs "^[^#]*$strict_rules_package" \
        "$1/analysis_options.yaml"; then
        echo "checks: $1/analysis_options.yaml must include" >&2
        echo "checks: ${strict_rules_package}analysis_options.yaml" >&2
        exit 1
    fi
}

is_flutter_package() {
    grep -qsE '^[[:space:]]+sdk:[[:space:]]*flutter[[:space:]]*$' \
        "$1/pubspec.yaml"
}
