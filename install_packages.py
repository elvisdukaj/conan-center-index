#!python3

import itertools
import subprocess
import platform
import functools
import operator
import click

from pathlib import Path
from install_utils.install_utils import get_folder_from_yaml, should_skip_line

packages_filename = "packages.list"
packages_platform_filename = f"packages_{platform.system().lower()}.list"
packages_x86_64_filename = "packages_x86-x86_64.list"
tools_filename = f"tools_{platform.system().lower()}.list"


def conan_export(name, folder, version, dry_run: bool = False):
    cmd_line = ["conan", "export", f"./recipes/{name}/{folder}", f"--version={version}"]

    if dry_run:
        print(f"Calling {cmd_line}")
    else:
        subprocess.check_call(cmd_line)


def conan_create(name, folder, version, profile, build_types, archs, libcxxs, cppstds, api_levels, dry_run: bool = False):
    build_types_args: list[list[str]] = [["-s", f"build_type={build_type}"] for build_type in build_types]
    archs_args: list[list[str]] = [["-s", f"arch={arch}"] for arch in archs]
    libcxxs_args: list[list[str]] = [["-s", f"compiler.libcxx={libcxx}"] for libcxx in libcxxs]
    cppstds_args: list[list[str]] = [["-s", f"compiler.cppstd={cppstd}"] for cppstd in cppstds]
    api_levels_args: list[list[str]] = [["-s", f"os.api_level={api_level}"] for api_level in api_levels]

    # cartesian product filtering empty elements
    for args in itertools.product(build_types_args or [[]],
                                  archs_args or [[]],
                                  libcxxs_args or [[]],
                                  cppstds_args or [[]],
                                  api_levels_args or [[]]):
        # filter empty elements and flat the map
        non_empty_args = list(filter(None, args))
        flat_args = [] if not non_empty_args else functools.reduce(operator.concat, non_empty_args)

        cmd_line = ["conan", "create", f"./recipes/{name}/{folder}", f"--version={version}",
                    f"--profile={profile}",
                    *flat_args]
                    # "--build=missing"]
        if dry_run:
            print("Calling", cmd_line)
        else:
            subprocess.check_call(cmd_line)


def conan_upload(name, version, dry_run: bool = False):
    cmd_line = ["conan", "upload", f"{name}/{version}", "-r", "local"]
    if dry_run:
        print("Calling", cmd_line)
    else:
        subprocess.check_call(cmd_line)


def build_package(build_package: bool, upload_package: bool, filename, build_configuration, dry_run, filter: list[str]):
    with open(filename, "r") as packages_file:
        for line in packages_file:
            if should_skip_line(line):
                continue

            name, version = line.strip().split("/")
            yaml_path = Path(f"./recipes/{name}/config.yml")
            folder = get_folder_from_yaml(filename=yaml_path, version=version)

            if len(filter) != 0:
                if f"{name}/{version}" not in filter:
                    continue

            # The upload can occurs once after all the build configurations are built
            conan_export(name=name, folder=folder, version=version, dry_run=dry_run)

            for profile in build_configuration:
                build_types: list[str] = build_configuration[profile].get("build_types") or []
                archs: list[str] = build_configuration[profile].get("archs") or []
                libcxxs: list[str] = build_configuration[profile].get("libcxxs") or []
                cppstds: list[str] = build_configuration[profile].get("cppstd") or []
                api_level: list[str] = build_configuration[profile].get("os.api_level") or []

                if build_package:
                    conan_create(name=name, folder=folder, version=version, profile=profile,
                                 build_types=build_types, archs=archs, cppstds=cppstds, libcxxs=libcxxs,
                                 api_levels=api_level, dry_run=dry_run)

            if upload_package:
                # The upload can occurs once after all the build configurations are built
                conan_upload(name=name, version=version, dry_run=dry_run)


def build_tools_with_conf(package_list_filename: str, configuration: dict, dry_run: bool):
    build_package(filename=package_list_filename, build_configuration=configuration, dry_run=dry_run)


@click.command()
@click.option("--build", is_flag=True, default=False, show_default=True, help="Build the package")
@click.option("--upload", "-u", is_flag=True, default=False, show_default=True, help="Upload the package")
@click.option("--dry-run", is_flag=True, default=False, show_default=True, help="Don't execute the command, show only the calls")
@click.option("--with-tools", "-t", is_flag=True, default=False, show_default=True, help="Build the tools")
@click.option("--with-packages", "-p", is_flag=True, default=False, show_default=True, help="Build the packages")
@click.option("--with-packages-x86-x86_64-only", is_flag=True, default=False, show_default=True, help="Build only packages for x86_64")
@click.option("--filter", "-f", default=[], multiple=True, show_default=True, help="Build the packages")
def build(build: bool, upload: bool, with_tools: bool, with_packages_x86_x86_64_only: bool, with_packages: bool, dry_run: bool, filter: list[str]):
    configurations = {
        "tools": {
            "default": {}
        },
        "packages-x86-x86_64-only": {
            "qcomm/android-r21e": {
                "archs": ["x86_64"],
                "build_types": ["Release"],
                "libcxxs": ["c++_shared", "c++_static"],
                # "cppstd": [17, 20]
            },
            "qcomm/android-r25c": {
                "archs": ["x86_64"],
                "build_types": ["Debug", "Release"],
                "libcxxs": ["c++_static"],
                # "cppstd": [17, 20]
            },
            "default": {
                "archs": ["x86_64"],
                "build_types": ["Debug", "Release"],
            }
        },
        "packages": {
            "qcomm/android-r21e": {
                "archs": ["armv8", "x86_64"],
                "build_types": ["Debug", "Release"],
                "libcxxs": ["c++_static"],
            },
            "qcomm/android-r25c": {
                "archs": ["armv8", "x86_64"],
                "build_types": ["Debug", "Release"],
                "libcxxs": ["c++_static"],
            },
            "default": {
                "build_types": ["Debug", "Release"],
                "cppstd": [20],
            }
        },
        "packages_windows": {
            "default": {
                "build_types": ["Debug", "Release"],
                "cppstd": [20],
            }
        }
    }

    if with_tools:
        build_package(build_package=build, upload_package=upload,
                      filename=tools_filename, build_configuration=configurations["tools"], dry_run=dry_run, filter=filter)

    if with_packages_x86_x86_64_only:
        build_package(build_package=build, upload_package=upload,
                      filename=packages_x86_64_filename, build_configuration=configurations["packages-x86-x86_64-only"], dry_run=dry_run, filter=filter)

    if with_packages:
        build_package(build_package=build, upload_package=upload,
                      filename=packages_filename, build_configuration=configurations["packages"], dry_run=dry_run, filter=filter)

        if platform.system().lower() == "windows":
            build_package(build_package=build, upload_package=upload,
                          filename=packages_platform_filename, build_configuration=configurations["packages_windows"], dry_run=dry_run, filter=filter)


if __name__ == '__main__':
    build()
