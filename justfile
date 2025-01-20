release:
    #!/bin/bash
    VERSION=$(cat pyproject.toml | grep -oP '(?<=version = ")[^"]+')
    git tag "v$VERSION"
    git push origin "v$VERSION"
