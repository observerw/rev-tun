release:
    #!/bin/bash
    VERSION=$(sed -n 's/^version = "\([^"]*\)".*/\1/p' pyproject.toml)
    git tag "v$VERSION"
    git push origin "v$VERSION"
