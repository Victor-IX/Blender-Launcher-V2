load("@rules_python//python:defs.bzl", "py_library")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_library(
    name = "windows",
    srcs = glob(["*.py"]),
    visibility = ["//visibility:public"],
    deps = [
        "//source/modules:modules",
        "//source/widgets:widgets",
        "//source/threads:threads",
        requirement("pyside6-essentials"),
        requirement("semver"),
    ],
)
