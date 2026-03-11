# Project Guidelines

## Workflow
- Always commit and push immediately after making changes. Do not wait for the user to ask.
- Run in "yolo" / auto-accept mode — do not ask for permission before running tools. Just do it.

## Releasing
- After pushing changes, bump the version in package.json, commit, push, then create and push the corresponding git tag (e.g. `git tag v1.3.0 && git push origin v1.3.0`) to trigger the build workflow.
- First number: big milestones (2.0.0, 3.0.0)
- Second number: major updates / new features (1.1.0, 1.2.0) — reset third number to 0
- Third number: minor fixes, small changes (1.2.1, 1.2.2)
