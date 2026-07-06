## Summary

<!-- What changed and why? -->

## Type

- [ ] Bug fix
- [ ] Feature
- [ ] Transport/fallback change
- [ ] Documentation
- [ ] Tests/CI
- [ ] Maintenance

## Public-Only Boundary

- [ ] This change does not bypass authentication, paywalls, CAPTCHA, or private access controls.
- [ ] This change does not add credential collection or credential storage.
- [ ] New network behavior is limited to public content routes.

## Testing

<!-- Paste commands and relevant output. -->

- [ ] `uv run pytest`
- [ ] Manual smoke test, if network behavior changed:

```bash
uv run unlimited-search read https://example.com --max-attempts 1 --max-content-chars 300
```

## Notes

<!-- Risks, follow-ups, known limitations. -->
