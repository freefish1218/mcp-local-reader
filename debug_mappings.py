#!/usr/bin/env python
"""Debug parser mappings"""

from src.file_reader.parser_loader import parser_loader

print("Parser mappings:")
for ext, mapping in sorted(parser_loader.parser_mapping.items()):
    print(f"  {ext}: {mapping}")

print("\nChecking .py extension:")
if '.py' in parser_loader.parser_mapping:
    print("  ✅ .py is in parser_mapping")
    print(f"  Mapping: {parser_loader.parser_mapping['.py']}")
else:
    print("  ❌ .py is NOT in parser_mapping")

# Now check FileReader mappings
from src.file_reader.core import FileReader

reader = FileReader()
print("\nFileReader file_type_mapping:")
if '.py' in reader.file_type_mapping:
    print("  ✅ .py is in file_type_mapping")
    print(f"  Maps to: {reader.file_type_mapping['.py']}")
else:
    print("  ❌ .py is NOT in file_type_mapping")

print("\nAll text-related mappings in FileReader:")
for ext, parser_type in sorted(reader.file_type_mapping.items()):
    if parser_type == 'text':
        print(f"  {ext} -> {parser_type}")