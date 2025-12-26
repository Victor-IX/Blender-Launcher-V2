import re


def update_version_in_main_py(file_path, new_version):
    with open(file_path) as file:
        content = file.read()
        lines = content.splitlines()

        for i, line in enumerate(lines):
            stripped_line = line.lstrip()
            if 'prerelease="rc' in stripped_line and not stripped_line.startswith("#"):
                response = input(
                    "The current version is a prerelease version. This line needs to be commented out, continue? (y/n): "
                )
                if response.lower() == "y":
                    lines[i] = "# " + line

    content = "\n".join(lines)

    version_pattern = r"version = Version\(\s*([0-9]+),\n?\s*([0-9]+),\n?\s*([0-9]+),\n?"
    content = re.sub(
        version_pattern,
        "version = Version(\n    {},\n".format(new_version.replace(".", ",\n    ")),
        content,
    )

    content += "\n"

    with open(file_path, "w") as file:
        file.write(content)


def update_version_in_pyproject_toml(file_path, new_version):
    with open(file_path) as file:
        content = file.read()

    new_content = re.sub(r'version = "[0-9]+\.[0-9]+\.[0-9]+"', f'version = "{new_version}"', content)

    with open(file_path, "w") as file:
        file.write(new_content)


def update_version_in_version_txt(file_path, new_version):
    major, minor, patch = new_version.split(".")
    filevers = f"filevers=({major}, {minor}, {patch}, 0),"
    prodvers = f"prodvers=({major}, {minor}, {patch}, 0),"
    file_version_str = f"StringStruct(u'FileVersion', u'{new_version}')"
    product_version_str = f"StringStruct(u'ProductVersion', u'{new_version}')"

    with open(file_path) as file:
        content = file.read()

    content = re.sub(r"filevers=\([0-9]+, [0-9]+, [0-9]+, 0\),", filevers, content)
    content = re.sub(r"prodvers=\([0-9]+, [0-9]+, [0-9]+, 0\),", prodvers, content)
    content = re.sub(r"StringStruct\(u\'FileVersion\', u\'[0-9]+\.[0-9]+\.[0-9]+\'\)", file_version_str, content)
    content = re.sub(r"StringStruct\(u\'ProductVersion\', u\'[0-9]+\.[0-9]+\.[0-9]+\'\)", product_version_str, content)

    with open(file_path, "w") as file:
        file.write(content)


def update_version_in_doc(file_path, new_version, old_version):
    with open(file_path) as file:
        content = file.read()

    content = re.sub(old_version, new_version, content)

    with open(file_path, "w") as file:
        file.write(content)


def update_program_version(new_version):
    old_version_str = old_version()
    # Update versions in files
    update_version_in_main_py(main_py_path, new_version)
    update_version_in_pyproject_toml(pyproject_toml_path, new_version)
    update_version_in_version_txt(version_txt_path, new_version)
    update_version_in_doc(doc_path, new_version, old_version_str)

    print(f"Updated version to {new_version} in all files.")


def old_version():
    with open(pyproject_toml_path) as file:
        pyproject_content = file.read()
        return re.search(r'version = "([0-9]+\.[0-9]+\.[0-9]+)"', pyproject_content).group(1)


# Path
main_py_path = "./source/main.py"
doc_path = "./docs/mkdocs/index.md"
pyproject_toml_path = "./pyproject.toml"
version_txt_path = "./version.txt"

print("Current version is: ", old_version())
new_version = input("Enter the new version: ")
update_program_version(new_version)
