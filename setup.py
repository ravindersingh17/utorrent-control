from setuptools import setup

setup(
        name="ucontrol",
        version="1.1",
        description="Python bindings for utorrent API",
        author="Ravinder Singh",
        author_email="ravinder.sandhu@pm.me",
        install_requires=["requests", "bs4", "cython;platform_system=='cygwin'","PyCygwin;platform_system=='cygwin'"],
        packages=["utorrent-control"],
        python_requires=">=3",
        )

