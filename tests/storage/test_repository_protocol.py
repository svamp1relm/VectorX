"""ExperimentRepository must be import-safe without SQLAlchemy (no [postgres]
extra needed) and any conforming backend must structurally match it.
"""

import subprocess
import sys


def test_repository_module_does_not_import_sqlalchemy():
    # A fresh subprocess, not an in-process sys.modules check: other test
    # modules in this same pytest run may already have imported sqlalchemy,
    # which would make an in-process check pass or fail depending on test
    # order rather than on what vectorx.storage.repository itself imports.
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import vectorx.storage.repository; "
                "assert 'sqlalchemy' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_a_conforming_class_satisfies_the_protocol():
    from vectorx.storage.repository import ExperimentRepository

    class FakeRepository:
        def save_experiment(self, result) -> int:
            return 1

        def get_experiment(self, experiment_id: int):
            return None

        def list_experiment_ids(self) -> tuple[int, ...]:
            return ()

    assert isinstance(FakeRepository(), ExperimentRepository)


def test_a_non_conforming_class_does_not_satisfy_the_protocol():
    from vectorx.storage.repository import ExperimentRepository

    class NotARepository:
        pass

    assert not isinstance(NotARepository(), ExperimentRepository)
