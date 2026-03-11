# Project Guidelines

## Workflow
- Always commit and push immediately after making changes. Do not wait for the user to ask.
- Run in "yolo" / auto-accept mode — do not ask for permission before running tools. Just do it.

## Releasing
- After pushing changes, bump the version in package.json, commit, push, then create and push the corresponding git tag (e.g. `git tag v1.3.0 && git push origin v1.3.0`) to trigger the build workflow.
- For major updates (new features, big changes): bump the middle number and reset patch to 0 (e.g. 1.2.0 → 1.3.0)
- For minor updates (small fixes, text changes): bump the last number (e.g. 1.2.0 → 1.2.1)
