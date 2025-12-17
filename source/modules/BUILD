load("@rules_python//python:defs.bzl", "py_library")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_library(
    name = "modules",
    srcs = glob(["*.py"]),
    visibility = ["//visibility:public"],
    deps = [
        requirement("beautifulsoup4"),
        requirement("urllib3"),
        requirement("lxml"),
        requirement("distro"),
        requirement("semver"),
        requirement("zstandard"),
        requirement("send2trash"),
        requirement("webdav4"),
        requirement("dateparser"),
        requirement("pyside6-essentials"),
        requirement("markdown"),
        requirement("pynput"),
    ],
)
