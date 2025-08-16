# Pull Request

## Description

<!-- Provide a brief description of the changes and their purpose -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Maintenance/refactoring (code improvement without functional changes)
- [ ] 🧪 Test improvements

## Related Issues

<!-- Link to related issues using keywords like "Fixes #123" or "Closes #456" -->

Fixes #<!-- issue number -->

## Changes Made

<!-- Provide a detailed list of changes made -->

- 
- 
- 

## Testing

<!-- Describe how you tested these changes -->

### Test Categories Passed

- [ ] Unit tests (`uv run python tests/run_tests.py --models`)
- [ ] Parser tests (`uv run python tests/run_tests.py --parsers`)
- [ ] Core functionality tests (`uv run python tests/run_tests.py --core`)
- [ ] MCP server tests (`uv run python tests/run_tests.py --server`)
- [ ] All tests with coverage (`uv run python tests/run_tests.py -c`)

### Manual Testing

<!-- Describe manual testing performed -->

- [ ] Tested with Claude Desktop
- [ ] Tested with Claude Code
- [ ] Tested with different file types
- [ ] Tested error scenarios
- [ ] Tested performance with large files

### Test Files

<!-- If you added new test files or modified existing ones, list them here -->

- 
- 

## Configuration Changes

<!-- If your changes require configuration updates, describe them -->

- [ ] No configuration changes required
- [ ] New environment variables added (documented in README.md)
- [ ] Configuration format changed (migration guide provided)
- [ ] Default values updated

## Documentation Updates

<!-- Mark all documentation that was updated -->

- [ ] README.md updated
- [ ] CONTRIBUTING.md updated
- [ ] CLAUDE.md updated
- [ ] Code comments/docstrings updated
- [ ] No documentation changes needed

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improved
- [ ] Performance may be slightly impacted (justified in description)
- [ ] Significant performance changes (detailed analysis provided)

## Breaking Changes

<!-- If this is a breaking change, describe the impact and migration path -->

- [ ] No breaking changes
- [ ] Breaking changes documented below

### Migration Guide

<!-- If breaking changes exist, provide migration instructions -->

## Security Considerations

<!-- Address any security implications -->

- [ ] No security impact
- [ ] Security improvements made
- [ ] Potential security considerations addressed

## Dependencies

<!-- Note any dependency changes -->

- [ ] No new dependencies
- [ ] New dependencies added (justified and documented)
- [ ] Dependencies updated
- [ ] Dependencies removed

### New Dependencies

<!-- List any new dependencies and their purpose -->

## Screenshots/Examples

<!-- If applicable, add screenshots or examples showing the changes -->

## Checklist

<!-- Ensure all items are completed before requesting review -->

### Code Quality

- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is properly commented and documented
- [ ] No debugging code or comments left in

### Testing

- [ ] New tests added for new functionality
- [ ] All existing tests pass
- [ ] Edge cases considered and tested
- [ ] Error handling tested

### Documentation

- [ ] Documentation updated for user-facing changes
- [ ] API documentation updated if applicable
- [ ] Configuration documentation updated if applicable

### Compatibility

- [ ] Changes work on all supported Python versions (3.11+)
- [ ] Changes work on all supported operating systems
- [ ] Backward compatibility maintained (or breaking changes documented)

## Additional Notes

<!-- Any additional information for reviewers -->

## Review Focus Areas

<!-- Guide reviewers on what to focus on -->

Please pay special attention to:

- 
- 
- 

---

**For Maintainers:**

- [ ] Version bump needed
- [ ] Release notes entry needed
- [ ] Migration guide needed
- [ ] Blog post/announcement needed