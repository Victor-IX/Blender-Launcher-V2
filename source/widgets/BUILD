load("@rules_python//python:defs.bzl", "py_library")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_library(
    name = "widgets",
    srcs = glob(["*.py", "**/*.py"]),
    visibility = ["//visibility:public"],
    deps = [
        "//source/modules:modules",
        "//source/threads:threads",
        requirement("pyside6-essentials"),
        requirement("semver"),
        requirement("markdown"),
    ],
)
