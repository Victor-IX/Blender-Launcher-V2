load("@rules_python//python:defs.bzl", "py_library")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_library(
    name = "items",
    srcs = glob(["*.py"]),
    visibility = ["//visibility:public"],
    deps = [
        "//source/modules:modules",
        requirement("pyside6-essentials"),
    ],
)
