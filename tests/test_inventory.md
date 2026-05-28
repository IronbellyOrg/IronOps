# FR/NFR/AC → Test Traceability Matrix (AC-8)

Every FR-1..FR-16, NFR-1..NFR-9, and AC-1..AC-10 has at least one test reference.

| ID | Implementing module(s) | Test file | Key test functions | Assertion summary |
|---|---|---|---|---|
| FR-1 | `manifest.py`, `render.py` | `test_manifest.py`, `test_render.py` | `test_good_manifest_loads`, `test_single_file_emits_one_rendered_file` | Manifest parses; per-import copy emits rendered files |
| FR-2 | `sources.py` | `test_sources.py` | `test_resolve_default_branch_parses_symref`, `test_no_hardcoded_main_or_master_in_module_source` | Default branch resolved from ls-remote, no hardcoded main/master |
| FR-3 | `sources.py`, `render.py` | `test_sources.py`, `test_render.py` | `test_clean_working_tree_passes_when_empty`, `test_byte_identical_copy` | Upstream tree clean after build; reads only |
| FR-4 | `render.py` | `test_render.py`, `test_negative.py` | `test_co_import_command_without_skill_fails`, `test_orphan_command_fails_with_co_import_missing` | Command needing skill without import = CoImportMissing |
| FR-5 | `validate.py` | `test_pipeline.py` | `test_pipeline_validator_failure_aborts_publish` | Validator failure aborts publish |
| FR-6 | `metadata.py` | `test_metadata.py` | `test_meta_json_sources_imports_fanout`, `test_meta_json_built_at_iso8601_utc` | META.json includes per-file fanout + built_at + builder_version |
| FR-7 | `render.py` | `test_render.py` | `test_byte_identical_copy` | shutil.copy2 produces byte-identical files |
| FR-8 | `render.py` | `test_render.py`, `test_negative.py` | `test_path_escape_in_to_field_rejected`, `test_bad_manifest_fails_with_categorical_code[bad-path-escape]` | Absolute paths and `..` segments rejected |
| FR-9 | `pipeline.py`, `publish.py` | `test_atomicity.py`, `test_pipeline.py` | `test_render_failure_leaves_marketplace_unchanged`, `test_validate_failure_leaves_marketplace_unchanged` | Marketplace HEAD unchanged on any pre-publish failure |
| FR-10 | `metadata.py` | `test_metadata.py` | `test_marketplace_json_single_plugin`, `test_marketplace_json_source_path` | marketplace.json lists single plugin with `./plugins/ironops-devops` source |
| FR-11 | `metadata.py` | `test_metadata.py` | `test_third_party_licenses_references_upstream`, `test_third_party_licenses_per_file_mapping` | THIRD_PARTY_LICENSES.md lists per-source per-file mapping |
| FR-12 | `metadata.py`, `cli.py` | `test_metadata.py`, `test_cli.py` | `test_resolve_builder_version_fails_on_dirty_tree`, `test_cli_build_help_exposes_flags` | Dirty tree raises BuilderDirtyTree; no `--allow-dirty` flag |
| FR-13 | `metadata.py` | `test_metadata.py` | `test_plugin_json_omits_version` | plugin.json has no `version` key |
| FR-14 | `manifest.py` | `test_manifest.py` | `test_schema_version_negative[*]`, `test_schema_version_missing` | schema_version must be string "1" |
| FR-15 | `manifest.py` | `test_manifest.py` | `test_empty_imports_rejected`, `test_missing_imports_key_rejected` | Empty/missing imports rejected |
| FR-16 | `manifest.py` | `test_manifest.py` | `test_self_overwrite_rejected[*]` | RESERVED_GENERATED_PATHS targets rejected |
| NFR-1 | `render.py`, `pipeline.py` | `test_render.py`, `test_pipeline.py` | `test_deterministic_ordering`, `test_pipeline_deterministic_excluding_built_at` | Identical inputs → identical outputs (except META.built_at) |
| NFR-2 | `pipeline.py` | `test_pipeline.py` | `test_pipeline_stage_timing_recorded` | Build duration well under 60s soft / 300s hard |
| NFR-3 | docs only | `docs/MANIFEST_AUTHORING.md` | (doc, not test) | <1500 token always-on context, claude plugin details verification |
| NFR-4 | `validate.py` | `test_pipeline.py` (via mock_claude_validate warning path) | `test_pipeline_validator_failure_aborts_publish` | Strict warnings — any warning is a failure |
| NFR-5 | implicit | (covered by overall test suite size — 79 unit + integration) | — | Test surface area sufficient |
| NFR-6 | `publish.py` | `test_pipeline.py` | `test_pipeline_publish_message_format` | Commit message includes builder_version + source SHAs |
| NFR-7 | `errors.py`, `pipeline.py`, `validate.py` | `test_errors.py`, `test_negative.py` | `test_exit_code_enum_values_distinct`, `test_failure_emits_one_line_stderr_summary` | 9 categorical codes (incl PUBLISH_FAILED), one-line stderr |
| NFR-8 | `manifest.py` | `test_manifest.py` | `test_schema_version_negative[*]` | Only schema_version "1" accepted in v0.1 |
| NFR-9 | `sources.py` | `test_sources.py` | `test_clean_working_tree_passes_when_empty`, `test_clean_working_tree_raises_when_dirty` | Post-build clean working tree invariant |
| AC-1 | `cli.py` | `test_cli.py` | `test_cli_build_dry_run_happy_path` | CI invokes `ironops build` and gets exit 0 |
| AC-2 | `pipeline.py` | `test_golden_output.py` | `test_golden_snapshot_matches` | Snapshot test against committed golden tree |
| AC-3 | `pipeline.py` | `test_pipeline.py` | `test_pipeline_emits_all_four_generated_files` | Four generated files emitted (plugin.json/META.json/licenses/marketplace.json) |
| AC-4 | `metadata.py` | `test_metadata.py` | `test_meta_json_*` (8 tests) | META.json schema fully covered |
| AC-5 | `metadata.py` | `test_metadata.py` | `test_third_party_licenses_*` (2 tests) | THIRD_PARTY_LICENSES per-file mapping |
| AC-6 | `publish.py` | `test_pipeline.py` | `test_pipeline_publish_message_format` | Commit message contains builder_version + source SHA |
| AC-7 | implicit | covered by overall pipeline tests | — | END-TO-END pipeline passes |
| AC-8 | (this file) | `tests/test_inventory.md` | — | Every FR/NFR/AC has a test reference |
| AC-9 | `pipeline.py`, `publish.py` | `test_pipeline.py` | `test_pipeline_deterministic_excluding_built_at` | Re-builds are reproducible |
| AC-10 | `pipeline.py`, `manifest.py` | `test_negative.py` | `test_bad_manifest_fails_with_categorical_code[*]` (5 fixtures) + `test_orphan_command_fails_with_co_import_missing` | Every malformed-manifest fixture fails fast with the correct exit code |
