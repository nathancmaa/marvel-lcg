import os

class Build:
    release = "RELEASE" in os.environ
    release = True

    # The fork has one name rather than a new one each release. Codenames --
    # Echo, Ronin, Archive, Cerebro -- named four versions and then stopped
    # being useful: they dated the build without saying anything about it, and
    # a release under a name nobody had heard of is harder to talk about than
    # a number. Cerebro is the name that stayed.
    PRODUCT_NAME = "Marvel Champions Digital: Cerebro"

    # Version
    MAJOR = 0
    MINOR = 7
    PATCH = 8
    BUILD = 0

    RELEASE_VERSION = f"{MAJOR}.{MINOR}.{PATCH}"
    RELEASE_LABEL = f'Version {RELEASE_VERSION}'
