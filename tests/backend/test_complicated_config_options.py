import pytest
from semver import Version

from source.modules.settings import (
    get_version_specific_queries,
    set_version_specific_queries,
)
from source.modules.version_matcher import VersionSearchQuery
from tests.config import SKIP_TESTS_THAT_MODIFY_CONFIG


@pytest.mark.skipif(SKIP_TESTS_THAT_MODIFY_CONFIG, reason="Tests that modify the config is disabled")
class TestConfig:
    def test_saving_vsq(self):
        version_specific_queries = {
            Version(4, 2, 0): VersionSearchQuery.version(4, "^", "^", branch=("daily",)),
            Version(2, 80, 0): VersionSearchQuery.version(2, "^", "^", commit_time="^"),
        }

        set_version_specific_queries(version_specific_queries)
        retrieved = get_version_specific_queries()

        assert version_specific_queries.keys() == retrieved.keys()
        assert all(hash(v) == hash(retrieved[k]) for k, v in version_specific_queries.items())
        for k, v in version_specific_queries.items():
            assert hash(v) == hash(retrieved[k])
