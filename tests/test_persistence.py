from pathlib import Path

from src.app.persistence.filesystem import FileStorage


def test_file_storage_creates_run_directory(tmp_path: Path) -> None:
    storage = FileStorage(root=tmp_path)
    run_dir = storage.make_run_directory(prefix="zones_test")

    assert run_dir.exists()
    assert run_dir.is_dir()
    assert run_dir.parent == tmp_path / "outputs"


def test_file_storage_writes_json_and_csv(tmp_path: Path) -> None:
    storage = FileStorage(root=tmp_path)
    run_dir = storage.make_run_directory(prefix="zones_test")

    summary_path = run_dir / "summary.json"
    assignments_path = run_dir / "assignments.csv"

    storage.write_json(summary_path, {"hello": "world"})
    storage.write_csv(assignments_path, "a,b\n1,2\n")

    assert summary_path.read_text(encoding="utf-8") == '{\n  "hello": "world"\n}'
    assert assignments_path.read_text(encoding="utf-8") == "a,b\n1,2\n"
