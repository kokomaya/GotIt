"""Tests for FilterRules — load/save YAML, path matching, defaults."""

from __future__ import annotations

from gotit.services.filter_rules import (
    DEFAULT_EXCLUDED_EXTENSIONS,
    DEFAULT_EXCLUDED_FILENAMES,
    DEFAULT_EXCLUDED_PATHS,
    FilterRules,
)


class TestShouldExclude:
    def test_git_directory(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\repo\\project\\.git\\HEAD")

    def test_git_directory_as_folder(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\repo\\project\\.git")

    def test_node_modules(self):
        rules = FilterRules()
        assert rules.should_exclude("C:\\app\\node_modules\\lodash\\index.js")

    def test_pycache(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\project\\__pycache__\\main.cpython-312.pyc")

    def test_recycle_bin(self):
        rules = FilterRules()
        assert rules.should_exclude("C:\\$RECYCLE.BIN\\something.txt")

    def test_normal_path_not_excluded(self):
        rules = FilterRules()
        assert not rules.should_exclude("D:\\Work\\project\\main.py")

    def test_normal_docx_not_excluded(self):
        rules = FilterRules()
        assert not rules.should_exclude("C:\\Users\\test\\report.docx")

    def test_office_temp_file(self):
        rules = FilterRules()
        assert rules.should_exclude("C:\\docs\\~$report.docx")

    def test_desktop_ini(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\folder\\desktop.ini")

    def test_pyc_extension(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\project\\module.pyc")

    def test_obj_extension(self):
        rules = FilterRules()
        assert rules.should_exclude("C:\\build\\file.obj")

    def test_case_insensitive_path(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\repo\\.GIT\\config")

    def test_case_insensitive_filename(self):
        rules = FilterRules()
        assert rules.should_exclude("D:\\folder\\DESKTOP.INI")

    def test_custom_rules(self):
        rules = FilterRules(
            excluded_paths=["build_output"],
            excluded_filenames=[],
            excluded_extensions=[],
        )
        assert rules.should_exclude("D:\\project\\build_output\\artifact.zip")
        assert not rules.should_exclude("D:\\project\\.git\\HEAD")


class TestToEverythingExcludes:
    def test_generates_excludes(self):
        rules = FilterRules(
            excluded_paths=[".git", "node_modules"],
            excluded_filenames=[],
            excluded_extensions=[],
        )
        excludes = rules.to_everything_excludes()
        assert "!path:.git" in excludes
        assert "!path:node_modules" in excludes

    def test_default_rules_generate_excludes(self):
        rules = FilterRules()
        excludes = rules.to_everything_excludes()
        # Paths with spaces or $ are skipped (handled by code-layer filter)
        safe_paths = [p for p in DEFAULT_EXCLUDED_PATHS if " " not in p and "$" not in p]
        assert len(excludes) == len(safe_paths)

    def test_excludes_skip_paths_with_spaces(self):
        rules = FilterRules(
            excluded_paths=[".git", "System Volume Information", "$RECYCLE.BIN"],
            excluded_filenames=[], excluded_extensions=[],
        )
        excludes = rules.to_everything_excludes()
        assert excludes == ["!path:.git"]


class TestLoadSave:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "filters.yaml")
        rules = FilterRules(
            excluded_paths=[".git", "custom_dir"],
            excluded_filenames=["*.tmp"],
            excluded_extensions=["log"],
        )
        rules.save(path)

        loaded = FilterRules.load(path)
        assert loaded.excluded_paths == [".git", "custom_dir"]
        assert loaded.excluded_filenames == ["*.tmp"]
        assert loaded.excluded_extensions == ["log"]

    def test_load_creates_default_if_missing(self, tmp_path):
        path = str(tmp_path / "nonexistent" / "filters.yaml")
        rules = FilterRules.load(path)
        assert rules.excluded_paths == DEFAULT_EXCLUDED_PATHS
        assert rules.excluded_filenames == DEFAULT_EXCLUDED_FILENAMES
        assert rules.excluded_extensions == DEFAULT_EXCLUDED_EXTENSIONS
        assert (tmp_path / "nonexistent" / "filters.yaml").is_file()

    def test_load_empty_yaml_uses_defaults(self, tmp_path):
        path = tmp_path / "filters.yaml"
        path.write_text("")
        rules = FilterRules.load(str(path))
        assert rules.excluded_paths == DEFAULT_EXCLUDED_PATHS
