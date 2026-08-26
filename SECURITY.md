# Security

## Scope

This is a documentation-and-prompt skill for Claude Code. It ships no service and
no binary. The security-relevant surface is small but real:

- `execute_blender_code` runs arbitrary Python inside Blender. Anything the skill
  tells a model to execute runs with your user's privileges.
- The pipeline downloads assets from PolyHaven and Sketchfab, and can fetch
  generation results from remote services.
- `tools/` scripts run in CI and locally.

## Reporting

Open a [security advisory](https://github.com/elithril/blender-kiln/security/advisories/new)
rather than a public issue. Include the version or commit, your Blender version,
and the smallest input that reproduces it.

Please do not include a working exploit in the initial report — describe the class
of problem and the affected path.

## What is not a vulnerability

- Blender Python running code you asked the skill to generate. That is what
  `execute_blender_code` is for.
- Assets from a marketplace being untrusted content. Verify licences and geometry
  before shipping them; the skill's own logs record licences for that reason
  (iron rule 17).
