load("@rules_python//python:defs.bzl", "py_library")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_library(
    name = "resources",
    srcs = ["__init__.py"],
    data = glob([
        "api/**/*",
        "certificates/**/*",
        "fonts/**/*",
        "icons/**/*",
        "styles/**/*",
        "*.qrc",
    ]),
    visibility = ["//visibility:public"],
)
