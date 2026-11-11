# checks

Static-analysis checks for Python, TypeScript, PHP, Dart and Rust. A
repository keeps one file, `checks.toml`, and the toolkit runs the checks
that match each folder's language.

## Use it in a repository

1. Add `checks.toml` at the repository root:

   ```toml
   source_directories = [
       "user-service/src",
       "user-service/tests",
       "ui-service/src",
       "ui-service/tests",
   ]
   ```

2. Install it (installs the tools, turns the git hooks on, ignores `.checks/`):

   ```sh
   git clone https://github.com/Frunnze/checks .checks
   .checks/install.sh
   ```

3. Commit. Run by hand with `.checks/run`, or one check with
   `.checks/run linters`. The pre-push hook checks the branch you have
   checked out, so it refuses to push commits that branch does not hold -
   push each branch from its own checkout.

Needs `python3` 3.12+, `node`, `composer` (PHP), `dart` and `osv-scanner`
(Dart), `cargo` 1.97+ and `rustup` on `PATH` (Rust) and `gitleaks`. Only
the folders in `source_directories` are checked, plus the root PHP files
of a WordPress package (below).
`coverage`, `api-contract` and `property-tests` read the `tests` folder next
to each source folder and fail unless it is listed too. Code in an
unsupported language is reported as unchecked.

## Use it in GitHub Actions

```yaml
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: npm ci --prefix ui
      - uses: Frunnze/checks@main
```

Install the repository's own dependencies first. The action runs every
enabled check over the whole repository.

## Checks

| Name | Description | Languages | Tools | Stability | Whitelist entry |
| --- | --- | --- | --- | --- | --- |
| `secrets` | No secret is committed | all | gitleaks | stable | finding fingerprint |
| `file-length` | No file over its language's `max-lines` | all | - | stable | path |
| `duplicate-code` | No copied code | Python, TS, PHP, Dart, Rust | jscpd | stable | glob |
| `semantic-duplicates` | No logic repeated in other words | Python, TS, PHP | onnxruntime, tree-sitter | experimental | finding text |
| `dead-code` | Nothing unreachable | Python, TS, PHP, Dart, Rust | vulture, knip, phpstan, dart_code_linter, rustc | stable | vulture name |
| `linters` | Style and bug-prone patterns | Python, TS, PHP, Dart, Rust | ruff, pylint, eslint, phpcs, dart analyze, clippy, rustfmt | stable | `tool:rule` |
| `unused-deps` | Declared dependencies match imports | Python, TS, PHP, Dart, Rust | deptry, knip, composer-dependency-analyser, dependency_validator, cargo-machete | stable | - |
| `vulnerable-deps` | No dependency with a known advisory | Python, TS, PHP, Dart, Rust | pip-audit, npm audit, composer audit, osv-scanner, cargo-audit | stable | advisory id |
| `security-patterns` | No insecure dataflow | Python, TS, PHP, Rust | semgrep | stable | rule id |
| `strict-typing` | Strict types, no silencing | Python, TS, PHP, Dart, Rust | basedpyright, tsc, phpstan, dart analyze, cargo check | stable | folder (PHP) |
| `coverage` | Every line and branch tested | Python, TS, PHP, Dart, Rust | pytest-cov, package script, phpunit, dart test, cargo-llvm-cov | stable | - |
| `single-responsibility` | No class or module with unrelated method groups | Python, TS, PHP | onnxruntime, tree-sitter | experimental | finding text |
| `feature-isolation` | Features meet only in `shared` | Python, TS, PHP | own finder | experimental | finding text |
| `open-closed` | No variants branched on in two or more places | Python, TS, PHP | tree-sitter | experimental | finding text |
| `dependency-inversion` | Collaborators injected, not built | Python | own finder | experimental | finding text |
| `definition-names` | No `and`/`or` in names | Python, TS | own finder | experimental | finding text |
| `nested-definitions` | No function inside a function | Python, TS | own finder | experimental | finding text |
| `property-tests` | Four property tests per function | Python, TS, PHP, Dart | own finder | experimental | finding text |
| `api-contract` | No generated request crashes an endpoint | Python | schemathesis | experimental | - |

## checks.toml

```toml
source_directories = ["api/src", "api/tests", "ui/src", "ui/tests"]
stable = "pre-commit"

[checks.coverage]
when = "pre-push"
source_directories = ["api/src", "api/tests"]

[checks.linters]
when = "both"
scope = "changed"
whitelist = ["ruff:S311", "eslint:no-console"]

[checks.file-length]
max-lines = 400

[checks.file-length.max-lines-by-language]
rust = 500
dart = 300

[checks.open-closed]
when = "pre-push"
```

- `stable`: the hook every stable check runs at - `pre-commit` (default),
  `pre-push`, `both` or `off`.
- `[checks.<name>]` overrides one check: `when` (same values; experimental
  checks are `off` until set), `scope` (`repository` or `changed`; not
  for `secrets`, which scans every change), `whitelist`,
  `source_directories`, and `max-lines` / `fail-under` /
  `code-similarity` / `word-overlap`.
- `[checks.file-length.max-lines-by-language]` gives a language its own
  limit (`python`, `typescript`, `php`, `dart` or `rust`, 1 to 100000);
  a language it leaves out keeps `max-lines`.
- `single-responsibility` and `semantic-duplicates` embed every function
  with the jina code model (about 640 MB, downloaded by `install.sh`
  into `.models/`; vectors are cached in `.cache/`). Two methods belong
  together when their code is `code-similarity` percent alike (default
  50) or they share `word-overlap` percent of their identifier words
  (default 20); a class or module fails when its methods, constructors
  aside, fall into two or more groups of two or more.
  `semantic-duplicates` reports two functions of five or more lines in
  one language whose code is `code-similarity` percent alike (default
  85), except same-named methods of two classes.
- `open-closed` reads the head of every `if`, `elif`, `elseif` and `case`
  branch and groups the rare names that travel together across
  functions. A function fails when two of its branches compare one
  subject against different quoted or capitalized values of a family
  of three or more, and another function does the same: adding a
  variant then edits every such place.
- Tools take their own options under their check, for example
  `[checks.linters.ruff]`, `[checks.linters.eslint]`, `[checks.linters.phpcs]`,
  `[checks.strict-typing.phpstan]`.
- A PHP package with `"type": "wordpress-plugin"` (or `wordpress-theme`) in
  `composer.json` gets the WordPress rules automatically, and owns the PHP
  files at the repository root (the plugin's main file and `uninstall.php`):
  `linters`, `strict-typing`, `security-patterns` and `dead-code` check them
  with the package.
- A Dart package lists `lib` and `tests` (or the Dart-style `test`, when the
  package has `test` and no `tests`) and keeps them resolved with
  `dart pub get`. A Flutter package (`sdk: flutter` in `pubspec.yaml`) runs
  its coverage with `flutter test`. Its `analysis_options.yaml` includes
  `package:very_good_analysis/analysis_options.yaml` (a dev dependency) and
  keeps the strict modes on; turn `public_member_api_docs` off there if you
  write no doc comments. `dead-code` counts a declaration as used when the
  package's library exports it (`export 'src/sign.dart';`). `coverage` runs
  `dart test tests` (package:test 1.27+) with every library loaded, so a
  file no test imports counts as untested. `property-tests` wants four
  kiri_check `property('<function> property <guarantee>', ...)` tests; an
  `@override` of a member the package never declares (a framework hook such as
  `paint` or `dispose`) needs none.
  `security-patterns` has no Dart rules yet - semgrep's Dart support is
  experimental.
- A Rust package is the folder holding `Cargo.toml`, a workspace member too:
  list `rust/crates/core/src` and `rust/crates/core/tests`. The checks run
  cargo in that folder, over all its targets. `linters` runs clippy with
  warnings denied and `cargo fmt --check`. `strict-typing` fails on
  `#[allow(...)]`, `#[expect(...)]` and their `cfg_attr` forms, then runs
  `cargo check` with `build.warnings = "deny"`. `dead-code` denies rustc's
  `unused` lints (rustc does not report a library's unused `pub` items).
  `unused-deps` runs cargo-machete on `[dependencies]` and honours
  `[package.metadata.cargo-machete] ignored`. `vulnerable-deps` runs
  cargo-audit on the workspace `Cargo.lock` and takes RustSec ids
  (`RUSTSEC-2022-0013`) in its whitelist. `coverage` runs cargo-llvm-cov and
  measures lines only - branch coverage needs nightly Rust.
  `security-patterns` uses semgrep's `p/rust` rules. `install.sh` adds
  clippy, rustfmt and llvm-tools-preview with rustup and installs
  cargo-machete, cargo-audit and cargo-llvm-cov from crates.io into
  `.cargo-tools/`.

## Develop

```sh
./install.sh
.venv/bin/python -m pytest tests
```

`checks/stable|experimental/<check>/<language>/check` holds each check;
`configuration/` reads `checks.toml`.
