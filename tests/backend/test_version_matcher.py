import datetime

from semver import Version

from source.modules.version_matcher import BasicBuildInfo, VersionSearchQuery

utc = datetime.timezone.utc  # noqa: UP017

builds = (
    BasicBuildInfo(Version.parse("1.2.3"), "stable", "", datetime.datetime(2020, 5, 4, tzinfo=utc)),
    BasicBuildInfo(Version.parse("1.2.2"), "stable", "", datetime.datetime(2020, 4, 2, tzinfo=utc)),
    BasicBuildInfo(Version.parse("1.2.1"), "daily", "", datetime.datetime(2020, 3, 1, tzinfo=utc)),
    BasicBuildInfo(Version.parse("1.2.4"), "stable", "", datetime.datetime(2020, 6, 3, tzinfo=utc)),
    BasicBuildInfo(Version.parse("3.6.14"), "lts", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
    BasicBuildInfo(Version.parse("4.2.0"), "stable", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
    BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 30, tzinfo=utc)),
    BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 28, tzinfo=utc)),
    BasicBuildInfo(Version.parse("4.3.1"), "daily", "", datetime.datetime(2024, 7, 20, tzinfo=utc)),
)


def test_matcher():
    # find the latest minor builds with any patch number
    results = VersionSearchQuery.version("^", "^", "*").match(builds)
    print(results)
    assert results == [
        BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 30, tzinfo=utc)),
        BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 28, tzinfo=utc)),
        BasicBuildInfo(Version.parse("4.3.1"), "daily", "", datetime.datetime(2024, 7, 20, tzinfo=utc)),
    ]

    # find any version with a patch of 14
    results = VersionSearchQuery.version("*", "*", 14).match(builds)
    assert results == [
        BasicBuildInfo(Version.parse("3.6.14"), "lts", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
    ]

    # find any version in the lts branch
    results = VersionSearchQuery.version("*", "*", "*", branch=("lts",)).match(builds)
    assert results == [
        BasicBuildInfo(Version.parse("3.6.14"), "lts", "", datetime.datetime(2024, 7, 16, tzinfo=utc)),
    ]

    # find the latest daily builds for the latest major release
    results = VersionSearchQuery.version("^", "*", "*", branch=("daily",), commit_time="^").match(builds)
    assert results == [
        BasicBuildInfo(Version.parse("4.3.0"), "daily", "", datetime.datetime(2024, 7, 30, tzinfo=utc)),
    ]

    # find oldest major release with any minor and largest patch
    results = VersionSearchQuery.version("-", "*", "^").match(builds)
    assert results == [
        BasicBuildInfo(Version.parse("1.2.4"), "stable", "", datetime.datetime(2020, 6, 3, tzinfo=utc)),
    ]

    print("test_binfo_matcher successful!")


def test_fuzzy_search():
    assert VersionSearchQuery(fuzzy_text="stbe").match(builds) == [b for b in builds if b.branch == "stable"]
    assert VersionSearchQuery(fuzzy_text="daly").match(builds) == [b for b in builds if b.branch == "daily"]
    assert VersionSearchQuery(fuzzy_text="07 16").match(builds) == [
        BasicBuildInfo(
            version=Version(major=3, minor=6, patch=14, prerelease=None, build=None),
            branch="lts",
            build_hash="",
            commit_time=datetime.datetime(2024, 7, 16, 0, 0, tzinfo=datetime.timezone.utc),
            folder=None,
            custom_name=None,
        ),
        BasicBuildInfo(
            version=Version(major=4, minor=2, patch=0, prerelease=None, build=None),
            branch="stable",
            build_hash="",
            commit_time=datetime.datetime(2024, 7, 16, 0, 0, tzinfo=datetime.timezone.utc),
            folder=None,
            custom_name=None,
        ),
    ]


def test_date_range_filtering():
    # after May 2020
    results = VersionSearchQuery(after=datetime.datetime(2020, 5, 1, tzinfo=utc)).match(builds)
    expected = [b for b in builds if b.commit_time >= datetime.datetime(2020, 5, 1, tzinfo=utc)]
    assert results == expected

    # before June 2020
    results = VersionSearchQuery(before=datetime.datetime(2020, 6, 1, tzinfo=utc)).match(builds)
    expected = [b for b in builds if b.commit_time <= datetime.datetime(2020, 6, 1, tzinfo=utc)]
    assert results == expected

    # range
    start = datetime.datetime(2020, 4, 1, tzinfo=utc)
    end = datetime.datetime(2020, 6, 1, tzinfo=utc)
    results = VersionSearchQuery(after=start, before=end).match(builds)
    expected = [b for b in builds if start <= b.commit_time <= end]
    assert results == expected


def test_vsq_serialization():
    for query in (
        VersionSearchQuery.any(),
        VersionSearchQuery.default(),
        VersionSearchQuery.version("^", "^", "*"),
        VersionSearchQuery.version("*", "*", 14),
        VersionSearchQuery.version("*", "*", "*", branch=("lts",)),
        VersionSearchQuery.version("^", "*", "*", branch=("daily",), commit_time="^"),
        VersionSearchQuery.version("-", "*", "^"),
        VersionSearchQuery.version(4, 0, 0),
        VersionSearchQuery.version(4, "*", "*"),
        VersionSearchQuery.version(
            "^",
            "^",
            "*",
            branch=("stable",),
            commit_time=datetime.datetime(2020, 5, 4, tzinfo=utc),
        ),
    ):
        result_before_serialization = query.match(builds)

        serialized_query = str(query)
        deserialized_query = VersionSearchQuery.parse(serialized_query)
        print(f"{serialized_query} -> {deserialized_query}")
        result_after_serialization = deserialized_query.match(builds)
        assert query == deserialized_query
        assert result_before_serialization == result_after_serialization

    print("test_vsq_serialization successful!")


def test_search_query_parser():
    # Test parsing of search query strings
    assert VersionSearchQuery.parse("1.2.3") == VersionSearchQuery(major=1, minor=2, patch=3)
    assert VersionSearchQuery.parse("^.*.-") == VersionSearchQuery(major="^", patch="-")
    assert VersionSearchQuery.parse("*.*.*-daily") == VersionSearchQuery(
        major="*", minor="*", patch="*", branch=("daily",)
    )
    assert VersionSearchQuery.parse("*.*.*+cb886aba06d5") == VersionSearchQuery.version(
        "*", "*", "*", build_hash="cb886aba06d5"
    )
    assert VersionSearchQuery.parse("*.*.*@2024-07-31T23:53:51+00:00") == VersionSearchQuery.version(
        "*", "*", "*", commit_time=datetime.datetime(2024, 7, 31, 23, 53, 51, tzinfo=utc)
    )
    assert VersionSearchQuery.parse("*.*.*@2024-07-31 23:53:51+00:00") == VersionSearchQuery.version(
        "*", "*", "*", commit_time=datetime.datetime(2024, 7, 31, 23, 53, 51, tzinfo=utc)
    )
    # Test parsing of search query strings that are not valid
    try:
        VersionSearchQuery.parse("abc")
        raise AssertionError("Expected ValueError to be raised")
    except ValueError:
        pass

    print("test_search_query_parser successful!")
