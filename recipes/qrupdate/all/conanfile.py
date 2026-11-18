from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import (
    copy,
    get,
    rmdir,
)
import os

required_conan_version = ">=2.0.9"


class QrupdateConan(ConanFile):
    name = "qrupdate"
    description = (
        "qrupdate-ng: a Fortran library for fast updates of QR and Cholesky decompositions "
        "(rank-1 updates, row/column insertion, deletion and shifts)."
    )
    license = "GPL-3.0-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gitlab.mpi-magdeburg.mpg.de/koehlerm/qrupdate-ng"
    topics = ("qr", "cholesky", "factorization", "linear-algebra", "fortran")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "openblas/*:build_lapack": True,
    }
    implements = ["auto_shared_fpic"]

    @property
    def _fortran_compiler(self):
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("fortran")

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openblas/[>=0.3.24 <1]")

    def validate(self):
        if not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires LAPACK: set -o openblas/*:build_lapack=True"
            )

    def validate_build(self):
        if not self._fortran_compiler:
            raise ConanInvalidConfiguration(
                f"{self.ref} needs a Fortran compiler: set it in the profile, e.g. "
                'tools.build:compiler_executables={"fortran": "gfortran"}'
            )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.20 <5]")
        self.tool_requires("pkgconf/[>=2.0 <4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_Fortran_COMPILER"] = self._fortran_compiler
        tc.cache_variables["BLA_PKGCONFIG_BLAS"] = "openblas"
        tc.cache_variables["BLA_PKGCONFIG_LAPACK"] = "openblas"
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["QRUPDATE_STATIC_WITH_PIC"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.cache_variables["QRUPDATE_C_INTERFACE"] = True
        tc.cache_variables["QRUPDATE_DOCS"] = False
        tc.cache_variables["INTEGER8"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qrupdate")
        self.cpp_info.set_property("cmake_target_name", "qrupdate::qrupdate")
        self.cpp_info.set_property("pkg_config_name", "qrupdate")
        self.cpp_info.libs = ["qrupdate"]
        self.cpp_info.includedirs = [os.path.join("include", "qrupdate")]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        if not self.options.shared:
            self.cpp_info.defines.append("QRUPDATE_STATIC")
            self.cpp_info.system_libs.append("gfortran")
