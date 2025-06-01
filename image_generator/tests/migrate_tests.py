#!/usr/bin/env python3
"""
Migration helper script for transitioning from legacy test system to new unified runner.

This script helps identify and organize test files according to the new categorization system.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List

class TestMigrator:
    """Helper class for migrating test structure"""
    
    def __init__(self):
        self.tests_dir = Path(__file__).parent
        self.backup_dir = self.tests_dir / "legacy_backup"
        
    def create_backup(self):
        """Create backup of legacy test structure"""
        print("Creating backup of legacy test scripts...")
        
        self.backup_dir.mkdir(exist_ok=True)
        
        legacy_files = [
            "run_correlation_tests.sh",
            "run_real_single_test.sh", 
            "cleanup_tests.sh",
            "test_upscale_correlation.sh"
        ]
        
        for file in legacy_files:
            source = self.tests_dir / file
            if source.exists():
                target = self.backup_dir / file
                shutil.copy2(source, target)
                print(f"  Backed up: {file}")
                
        print(f"Backup created in: {self.backup_dir}")
        
    def analyze_test_files(self) -> Dict[str, List[str]]:
        """Analyze existing test files and categorize them"""
        print("\nAnalyzing test file structure...")
        
        categorization = {
            'unit': [],
            'integration': [],
            'e2e': [],
            'uncategorized': []
        }
        
        # Scan unit tests
        unit_dir = self.tests_dir / "unit"
        if unit_dir.exists():
            for test_file in unit_dir.glob("test_*.py"):
                categorization['unit'].append(str(test_file.relative_to(self.tests_dir)))
                
        # Scan integration tests  
        integration_dir = self.tests_dir / "integration"
        if integration_dir.exists():
            for test_file in integration_dir.glob("test_*.py"):
                # Categorize based on filename patterns
                if 'live' in test_file.name or 'midjourney_integration' in test_file.name:
                    categorization['e2e'].append(str(test_file.relative_to(self.tests_dir)))
                else:
                    categorization['integration'].append(str(test_file.relative_to(self.tests_dir)))
                    
        # Scan root directory for miscategorized tests
        for test_file in self.tests_dir.glob("test_*.py"):
            if test_file.name not in ['test_config.py']:  # Skip config files
                categorization['uncategorized'].append(str(test_file.relative_to(self.tests_dir)))
                
        return categorization
        
    def generate_migration_report(self):
        """Generate a report showing the migration status"""
        categorization = self.analyze_test_files()
        
        print("\n" + "="*60)
        print("TEST MIGRATION ANALYSIS REPORT")
        print("="*60)
        
        for category, files in categorization.items():
            if files:
                print(f"\n{category.upper()} TESTS ({len(files)} files):")
                for file in files:
                    print(f"  ✓ {file}")
            else:
                print(f"\n{category.upper()} TESTS: None found")
                
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print(f"  Unit tests:      {len(categorization['unit'])} files")
        print(f"  Integration:     {len(categorization['integration'])} files") 
        print(f"  End-to-end:      {len(categorization['e2e'])} files")
        print(f"  Uncategorized:   {len(categorization['uncategorized'])} files")
        
        if categorization['uncategorized']:
            print(f"\n⚠️  WARNING: {len(categorization['uncategorized'])} files need manual categorization")
            
    def cleanup_legacy_files(self, confirm: bool = False):
        """Clean up legacy test runner files (with confirmation)"""
        legacy_files = [
            "run_correlation_tests.sh",
            "run_real_single_test.sh",
            "cleanup_tests.sh", 
            "test_upscale_correlation.sh"
        ]
        
        print("\nLegacy files that can be removed:")
        existing_files = []
        for file in legacy_files:
            file_path = self.tests_dir / file
            if file_path.exists():
                existing_files.append(file)
                print(f"  • {file}")
                
        if not existing_files:
            print("  No legacy files found to remove.")
            return
            
        if not confirm:
            print(f"\nTo remove these files, run:")
            print(f"  python migrate_tests.py --cleanup --confirm")
            return
            
        print(f"\nRemoving {len(existing_files)} legacy files...")
        for file in existing_files:
            file_path = self.tests_dir / file
            file_path.unlink()
            print(f"  Removed: {file}")
            
    def generate_usage_examples(self):
        """Generate usage examples for the new test system"""
        print("\n" + "="*60)
        print("NEW TEST SYSTEM USAGE EXAMPLES")
        print("="*60)
        
        examples = [
            ("Quick development feedback", "./run_tests.py --category quick"),
            ("Full unit test suite", "./run_tests.py --category unit"),
            ("Integration tests (mocked)", "./run_tests.py --category integration"),
            ("End-to-end tests (live API)", "./run_tests.py --category e2e"),
            ("CI-friendly unit tests", "./run_tests.py --category unit --ci --format json"),
            ("All tests in mock mode", "./run_tests.py --category all --mock-mode"),
            ("Verbose output with fail-fast", "./run_tests.py --category integration --verbose --fail-fast"),
            ("List available categories", "./run_tests.py --list")
        ]
        
        for description, command in examples:
            print(f"\n{description}:")
            print(f"  {command}")
            
    def create_team_migration_guide(self):
        """Create a migration guide for team members"""
        guide_content = """# Team Migration Guide: New Test System

## Quick Reference

### Old vs New Commands

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `./run_all_tests.sh 1` | `./run_tests.py --category unit` | All unit tests |
| `./run_all_tests.sh 2` | `./run_tests.py --category unit` | Same as above |
| `./run_all_tests.sh 3` | `./run_tests.py --category integration` | Integration tests |
| `./run_all_tests.sh 8` | `./run_tests.py --category e2e` | Live API tests |
| `./run_all_tests.sh 9` | `./run_tests.py --category all --mock-mode` | Auto mode equivalent |

### Quick Start

1. **Daily development**: `./run_tests.py --category quick`
2. **Before committing**: `./run_tests.py --category unit`
3. **Before PR**: `./run_tests.py --category integration`
4. **Release testing**: `./run_tests.py --category e2e` (manually)

### Key Benefits

- ✅ **Faster feedback**: Quick category runs in < 10 seconds
- ✅ **Better CI/CD**: Structured output and proper categorization
- ✅ **Cost control**: Clear separation of expensive vs. free tests
- ✅ **Easier debugging**: Verbose modes and better error reporting

### Migration Steps

1. **Update your aliases** (if any):
   ```bash
   # Replace old aliases
   alias test_unit="./run_tests.py --category unit"
   alias test_all="./run_tests.py --category integration"
   ```

2. **Update IDE run configurations**:
   - Replace old bash script calls with new Python script
   - Use `--verbose` flag for debugging

3. **Update documentation**:
   - Replace references to old numbered options
   - Use new category names in team docs

### Getting Help

- Run `./run_tests.py --list` to see all categories
- Check `TESTING_GUIDE.md` for comprehensive documentation
- Ask in team chat for migration questions

### Rollback Plan

The old `run_all_tests.sh` script remains available during transition period.
"""
        
        guide_path = self.tests_dir / "TEAM_MIGRATION_GUIDE.md"
        with open(guide_path, 'w') as f:
            f.write(guide_content)
            
        print(f"\nTeam migration guide created: {guide_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test system migration helper')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup of legacy test files')
    parser.add_argument('--analyze', action='store_true',
                       help='Analyze current test file structure')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up legacy test files')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirm destructive operations')
    parser.add_argument('--examples', action='store_true',
                       help='Show usage examples for new system')
    parser.add_argument('--team-guide', action='store_true',
                       help='Create team migration guide')
    parser.add_argument('--all', action='store_true',
                       help='Run all migration steps')
    
    args = parser.parse_args()
    
    migrator = TestMigrator()
    
    if args.all or args.backup:
        migrator.create_backup()
        
    if args.all or args.analyze:
        migrator.generate_migration_report()
        
    if args.all or args.examples:
        migrator.generate_usage_examples()
        
    if args.all or args.team_guide:
        migrator.create_team_migration_guide()
        
    if args.cleanup:
        migrator.cleanup_legacy_files(args.confirm)
        
    if not any([args.backup, args.analyze, args.cleanup, args.examples, args.team_guide, args.all]):
        # Default action: show analysis
        migrator.generate_migration_report()
        migrator.generate_usage_examples()

if __name__ == '__main__':
    main()