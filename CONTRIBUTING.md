# Contributing to EMC Principle Group Project

Thanks for your interest in contributing! This project follows the standard GitHub Flow workflow.

## Getting Started

1. **Fork** the repository and clone it locally.
2. Create a feature branch from `main`:

   ```powershell
   git checkout -b feat/your-feature-name
   ```

3. Make your changes with clear, focused commits.
4. Run linting and tests locally before pushing:

   ```powershell
   ruff check Codes/
   python -m pytest tests/ -v
   ```

## Pull Request Checklist

- [ ] Branch is created from the latest `main`
- [ ] Code passes `ruff check Codes/`
- [ ] New features are covered by tests
- [ ] Commit messages follow the Conventional Commits style (e.g. `feat:`, `fix:`, `docs:`, `test:`)
- [ ] README is updated if user-facing behavior changed

## Reporting Issues

Use [GitHub Issues](https://github.com/JesonChou/EMC_Principle_GroupProject/issues) to report bugs or request features. Please include:

- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Environment info: Python version, OS, model used (if any)

## Code of Conduct

Be respectful and constructive. This is an educational group project — keep contributions friendly and helpful.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
