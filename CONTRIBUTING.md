# Contributing to PACE

PACE decides how an AI agent communicates with the person it serves. It
only works if the people it serves, and the people who support them,
help shape it.

## You don't need to write code

If you live with a disability, care for someone, work in accessibility
or elder care, or you're a clinician or researcher, your experience is
the most useful input this project can get.

[Open an accessibility and capability feedback issue](https://github.com/ravikiran438/sauvidya-pace/issues/new?template=capability-feedback.yml).
It's a short form: what an agent would get wrong, and what should
happen instead. Some things we especially want to hear about:

- Capabilities PACE doesn't describe, or describes in a way that
  doesn't fit real people.
- Defaults that are wrong for you, such as two options per turn, a
  five-minute timeout, or the 0.7 language-fluency floor.
- Situations where a guardian, caregiver or relay helps, or gets in
  the way.
- Anything about consent: when a "yes" isn't really a yes.

The issue tracker is public, so please describe situations rather than
identifiable people, and leave out medical details. Write in whatever
language is easiest for you.

## Proposing a protocol change

Use the [spec change form](https://github.com/ravikiran438/sauvidya-pace/issues/new?template=spec-change.yml).
Name the invariant or field you want to change, the exact wording, and
whether it breaks existing payloads. Changes to normative behavior are
discussed in an issue before a pull request.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14+.

```bash
uv sync --all-extras
uv run pytest
uv run pace-mcp --doctor
```

Model checking needs Java 11+:

```bash
scripts/check-models.sh core augmentation witnesses mutants   # under a minute
scripts/check-models.sh                                       # everything
```

### Pull request checklist

- `uv run pytest` passes.
- If you changed a model, an endpoint or an invariant string,
  regenerate the manifests with `uv run python -m pace.manifest --write`
  and commit the result. A test fails when they drift.
- If you changed protocol behavior, update the TLA+ model where it
  applies and run `scripts/check-models.sh`. CI runs it on every push
  and pull request.
- Add an entry under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md),
  and mark wire-breaking changes **Breaking**.
- Use [Conventional Commits](https://www.conventionalcommits.org/)
  for commit messages, for example
  `fix(im-2): enforce language pins and fluency floor`.

## License

By contributing, you agree that your contributions are licensed under
the [Apache License 2.0](LICENSE).
