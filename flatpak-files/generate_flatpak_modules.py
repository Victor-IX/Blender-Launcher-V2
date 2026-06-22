# ruff: noqa: E402

# This generates the python3-modules.yaml file used in our flatpak packaging
# via our `uv.lock`file.


# The path to the lockfile used to resolve pip hashes and wheels.
LOCKFILE_PATH = "uv.lock"
# Output.
OUTPUT_PATH = "flatpak-files/python3-modules.yaml"

# The name of the target package.
ROOT_PACKAGE = "blender-launcher-v2"
# Toplevel dependencies to ignore.
IGNORE_DEPS = {
    "pyinstaller",  # irrelevant
    "pyside6-essentials",  # handled by io.qt.PySide.BaseApp
    "pynput",  # handled by external tools.
}
# Used to check system attributes against.
RUNTIME = "io.qt.PySide.BaseApp//6.10"

import shlex
import subprocess
import tomllib
from collections import deque

import yaml
from packaging.tags import Tag, create_compatible_tags_selector
from packaging.utils import parse_wheel_filename

with open(LOCKFILE_PATH, "rb") as f:
    t = tomllib.load(f)
    # We will probably have to rewrite parts of this if the revision changes
    assert t["revision"] == 3

# TODO sanitize output - serialize and deserialize?
s = subprocess.check_output(
    f'flatpak --arch=x86_64 --command=python3 run {RUNTIME} -c "from packaging import tags; print(list(map(str,tags.sys_tags())))"',
    shell=True,
)
valid_tags = {Tag(*t.split("-")) for t in eval(s.strip())}
print(f"{len(valid_tags)} valid tags for {RUNTIME}.")

packages = sorted(t["package"], key=lambda x: len(x["dependencies"]) if "dependencies" in x else 0)

tag_selector = create_compatible_tags_selector(valid_tags)

for p in packages:
    p.pop("source")
    if "sdist" in p:
        p["sdist"].pop("size")
        p["sdist"].pop("upload-time")
    if "wheels" in p:
        wheels = p["wheels"]

        found = False

        wheels = list(tag_selector((w, parse_wheel_filename(w["url"].split("/")[-1])[-1]) for w in wheels))

        p.pop("wheels")
        if wheels:
            p["wheel"] = wheels[0]
            wheels[0].pop("upload-time")
            wheels[0].pop("size")
            if "sdist" in p:
                p.pop("sdist")

root = next(p for p in packages if p["name"] == ROOT_PACKAGE)

root["dependencies"] = [dep for dep in root["dependencies"] if dep["name"] not in IGNORE_DEPS]

markers = sorted(
    {
        marker
        for pac in packages
        for marker in [
            x["marker"]
            for x in pac.get("dependencies", []) + list(pac.get("optional-dependencies", {}).values())
            if "marker" in x
        ]
    }
)


# check with Flatpak which of these are valid
#
# TODO properly sanitize
s = "\n".join(markers)
s = subprocess.check_output(
    f"""flatpak --arch=x86_64 --devel --command=python3 run {RUNTIME} \
    -c "from packaging.requirements import Marker; \
    print([Marker(x).evaluate() for x in \\"\\"\\"{s}\\"\\"\\".splitlines()])"
    """,
    shell=True,
)
x = eval(s)

markers = {marker for marker, valid in zip(markers, x, strict=True) if valid}
print()
name_to_package = {p["name"]: p for p in packages}

required_package_names = set()
visited_nodes = set()


def resolve_dependencies(pkgname, extra=None):
    # Track as "pkg" or "pkg[extra]"
    node_id = f"{pkgname}[{extra}]" if extra else pkgname

    if node_id in visited_nodes:
        return

    visited_nodes.add(node_id)
    required_package_names.add(pkgname)

    pkg = name_to_package[pkgname]

    if extra is None:
        deps = pkg.get("dependencies", [])
    else:
        deps = pkg.get("optional-dependencies", {}).get(extra, [])

    for dep in deps:
        if "marker" in dep and dep["marker"] not in markers:
            continue

        dep_name = dep["name"]

        # Always resolve the base package of a dependency
        resolve_dependencies(dep_name)

        # If this dependency requests extras (e.g. "extra": ["yaml"]), resolve them too
        requested_extras = dep.get("extra", []) or dep.get("extras", [])
        for req_extra in requested_extras:
            resolve_dependencies(dep_name, req_extra)


# trigger the resolver on the root package
# Note: to build docs/tests, trigger resolve_dependencies(ROOT_PACKAGE, "docs")
resolve_dependencies(ROOT_PACKAGE)

# remove unnecessary packages
packages = [p for p in packages if p["name"] in required_package_names]
name_to_package = {p["name"]: p for p in packages}  # Update lookup

all_deps = {}
for pkg in packages:
    # Base dependencies
    base_edges = [
        dep["name"]
        for dep in pkg.get("dependencies", [])
        if ("marker" not in dep or dep["marker"] in markers) and dep["name"] in required_package_names
    ]
    # We must also include dependencies from extras if those extras were resolved for this package
    extra_edges = [
        dep["name"]
        for extra, extra_deps in pkg.get("optional-dependencies", {}).items()
        if f"{pkg['name']}[{extra}]" in visited_nodes
        for dep in extra_deps
        if ("marker" not in dep or dep["marker"] in markers) and dep["name"] in required_package_names
    ]

    all_deps[pkg["name"]] = base_edges + extra_edges


# Sort the dependencies by build order
# https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
edges = [(frm, to) for to, deps in all_deps.items() for frm in deps]
L = []
S = deque(p for p, deps in all_deps.items() if len(deps) == 0)

while S:
    n = S.popleft()
    L.append(n)

    for edge in [e for e in edges if e[0] == n]:
        edges.remove(edge)
        if not any(e for e in edges if e[1] == edge[1]):
            S.appendleft(edge[1])  # most eager ordering
            # S.append(edge[1])  # least eager ordering


sorted_deps = {p: all_deps[p] for p in L}
sorted_deps.pop(ROOT_PACKAGE)

leaves = [pkg for pkg, deps in sorted_deps.items() if not deps]
print("Leaves:", ", ".join(leaves))
print("Dependencies:")
for pkg, deps in sorted_deps.items():
    if deps:
        print(f"{pkg} <- {', '.join(deps)}")


def source_from_package(d: dict) -> dict:
    # Once we have packages that use other forms of hashes
    # (if possible???), then we must change this
    if "wheel" in d:
        return {
            "type": "file",
            "url": d["wheel"]["url"],
            "sha256": d["wheel"]["hash"][d["wheel"]["hash"].index(":") + 1 :],
        }
    else:
        return {
            "type": "file",
            "url": d["sdist"]["url"],
            "sha256": d["sdist"]["hash"][d["sdist"]["hash"].index(":") + 1 :],
        }


source_ds: dict[str, dict] = {}
for pname in sorted_deps:
    actual_package = name_to_package[pname]

    if pname != "blender-launcher-v2":
        assert "wheel" in actual_package or "sdist" in actual_package, (
            f'package {pname} has no "sdist" or "wheel" source (How did we get here?)'
        )

    source_ds[pname] = source_from_package(actual_package)


modules = []
for module, source in source_ds.items():
    name = f"{module}=={name_to_package[module]['version']}"
    d = {
        "name": f"python3-{module}",
        "buildsystem": "simple",
        "build-commands": [
            " ".join(
                [
                    "pip3",
                    "install",
                    "--verbose",
                    "--exists-action=i",
                    "--no-index",
                    '--find-links="file://${PWD}"',
                    "--prefix=${FLATPAK_DEST}",
                    shlex.quote(name),
                    "--no-build-isolation",
                ]
            )
        ],
        "sources": [source],
    }
    modules.append(d)

d = {
    "name": "python3-modules",
    "buildsystem": "simple",
    "build-commands": [],
    "modules": modules,
}


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


IndentDumper.add_representer(dict, lambda d, dat: d.represent_dict(dat.items()))


with open(OUTPUT_PATH, "w") as output:
    output.write("# Autogenerated with Blender-Launcher-V2/flatpak-files/generate_flatpak_modules.py\n")
    yaml.dump(
        d,
        output,
        Dumper=IndentDumper,
        sort_keys=False,
    )

print(f"Wrote data to {OUTPUT_PATH}.")
