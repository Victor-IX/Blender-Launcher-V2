load("@rules_python//python:defs.bzl", "py_library")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_library(
    name = "threads",
    srcs = glob(["*.py"]),
    visibility = ["//visibility:public"],
    deps = [
        "//source/modules:modules",
        requirement("pyside6-essentials"),
        requirement("beautifulsoup4"),
        requirement("urllib3"),
        requirement("lxml"),
        requirement("zstandard"),
        requirement("send2trash"),
    ],
)
