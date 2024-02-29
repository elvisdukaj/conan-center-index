#!/usr/bin/python3
import pathlib
import subprocess
import yaml
import tempfile
from pathlib import Path
import re
import shutil

from install_utils.install_utils import get_folder_from_yaml, should_skip_line


def conan_create_graph(name, folder, version, profile, out_dir: Path):
    cmd_line = ["conan", "graph", "info", f"./recipes/{name}/{folder}", f"--version={version}",
                f"--profile={profile}", "--format=dot"]
    dot_output = subprocess.check_output(cmd_line).decode("utf-8")
    # replace "conanfile.py (<package>/<version>)" with "<package>/<version>"
    dot_output = dot_output.replace(f"conanfile.py ({name}/{version})", f"{name}/{version}")

    graph_path: Path = pathlib.Path(out_dir, f"{name}__{version}.dot")
    with open(str(graph_path), "w") as out_file:
        out_file.write(dot_output)


def build_package_graph(filename, profile, out_dir):
    with open(filename, "r") as packages_file:
        for line in packages_file:
            if should_skip_line(line):
                continue

            name, version = line.strip().split("/")
            yaml_path = Path(f"./recipes/{name}/config.yml")
            folder = get_folder_from_yaml(filename=yaml_path, version=version)

            conan_create_graph(name=name, folder=folder, version=version, profile=profile, out_dir=out_dir)


def get_graph_content(filepath: Path) -> str:
    with open(str(filepath), "r") as file:
        content = file.read()

        filename = str(filepath.name)

        if filename == "merged.dot":
            return ""

        name, version = re.match("(.+)__(.+)\.dot", str(filepath.name)).groups()

        # Remove the first line "digraph {"
        lines = content.splitlines()[1:]

        # remove the latest }
        lines = [line for line in lines if not re.match("^}.*", line)]

        # remove the android toolchain
        lines = [line for line in lines if not re.match(".*android-ndk/.*", line)]

        # remove the cmake
        lines = [line for line in lines if not re.match(".*cmake/.*", line)]

        # remove the ninja
        lines = [line for line in lines if not re.match(".*ninja/.*", line)]

        content = "\n".join(lines).strip()

        if len(content) == 0:
            content = f"        \"{name}/{version}\""

        print(f"Final content for {filename}:")
        print(content)

        return content


def merge_graphs(out_folder: Path, destination: Path):
    dot_files = out_folder.glob("**/*.dot")
    merged_file = Path(out_folder, "merged.dot")

    with open(str(merged_file), "w") as final_file:
        final_file.write("digraph {\n")

        for dot_file in dot_files:
            final_file.write(get_graph_content(dot_file))

        final_file.write("}\n")

    destination = destination / "merged.dot"
    shutil.copyfile(merged_file, destination)


if __name__ == '__main__':
    enable_build_packages = True

    packages_filename = "packages.list"

    with tempfile.TemporaryDirectory(".") as temporary_dir:
        print(f"Out folder is {temporary_dir}")
        build_package_graph(filename=packages_filename, profile="qcomm/android-r25c", out_dir=temporary_dir)
        merge_graphs(out_folder=Path(temporary_dir), destination=Path("."))
