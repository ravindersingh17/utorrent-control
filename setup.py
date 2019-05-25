from setuptools import setup

setup(
        name="ucontrol",
        version="1.1",
        description="Python bindings for utorrent API",
        author="Ravinder Singh",
        author_email="ravinder.sandhu@pm.me",
        install_requires=["requests", "bs4", "cython;sys_platform=='cygwin'","PyCygwin;sys_platform=='cygwin'"],
        packages=["ucontrol"],
        python_requires=">=3",
        )

