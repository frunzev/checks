rust_tool_root="$toolkit/.cargo-tools"
rust_tools="$rust_tool_root/bin"
rust_advisory_database="$rust_tool_root/advisory-db"
minimum_cargo_minor_version=97

require_cargo() {
    require_command cargo "brew install rustup, then put cargo on PATH"

    cargo_version=$(cargo --version)
    cargo_minor_version=$(printf '%s\n' "$cargo_version" \
        | sed -n 's/^cargo 1\.\([0-9][0-9]*\)\..*/\1/p')

    if [ -z "$cargo_minor_version" ] \
        || [ "$cargo_minor_version" -lt "$minimum_cargo_minor_version" ]
    then
        echo "checks: found $cargo_version, but the rust" >&2
        echo "checks: checks need cargo 1.$minimum_cargo_minor_version or" \
            "newer - run rustup update" >&2
        exit 1
    fi
}

require_rust_package() {
    if [ ! -f "$1/Cargo.toml" ]; then
        echo "checks: $1 has no Cargo.toml - list the src and tests" >&2
        echo "checks: folders of a rust package" >&2
        exit 1
    fi
}
