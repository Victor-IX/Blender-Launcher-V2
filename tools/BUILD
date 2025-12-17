load("@rules_python//python:defs.bzl", "py_binary")
load("@blender_launcher_pip//:requirements.bzl", "requirement")

py_binary(
    name = "rcc",
    srcs = ["rcc.py"],
    data = ["//source/resources"],
    deps = [requirement("pyside6-essentials")],
    visibility = ["//visibility:public"],
)
