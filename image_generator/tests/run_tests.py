#!/usr/bin/env python3
"""
Unified Test Runner for Silicon Sentiments Image Generator

This script provides a simplified interface for running tests with proper
categorization, environment validation, and CI/CD integration.
"""

import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

class TestRunner:
    """Unified test runner with categorization and CI support"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.test_output_dir = self.script_dir / "test_output"
        self.test_logs_dir = self.script_dir / "test_logs"
        
        # Test categories and their configurations
        self.test_categories = {
            'unit': {
                'description': 'Fast unit tests (< 30s)',
                'timeout': 30,
                'parallel': True,
                'mock_mode': True,
                'files': [
                    'unit/test_error_classes.py',
                    'unit/test_rate_limiter.py', 
                    'unit/test_simple_rate_limiter.py',
                    'unit/test_mock_client.py',
                    'unit/test_basic.py',
                    'unit/test_datetime_handling.py',
                    'unit/test_prompt_formatting.py',
                    'unit/test_variant_matching.py',
                    'unit/test_variation_name_handling.py',
                    'unit/test_upscale_buttons.py',
                    'unit/test_force_button_click.py',
                    'unit/test_upscale_processing.py'
                ]
            },
            'integration': {
                'description': 'Integration tests with mocked APIs (< 2 min)',
                'timeout': 120,
                'parallel': True,
                'mock_mode': True,
                'files': [
                    'integration/test_client_rate_limiting.py',
                    'integration/test_error_handling.py',
                    'integration/test_storage.py',
                    'integration/test_gridfs_storage.py',
                    'integration/test_slash_commands.py',
                    'integration/test_variation_naming_integration.py',
                    'integration/test_imagine_upscale_workflow.py',
                    'integration/test_upscale_correlation.py',
                    'integration/test_aspect_ratios.py',
                    'integration/test_discord_auth.py',
                    'integration/test_midjourney_workflow.py',
                    'integration/test_imagine_command_details.py',
                    'integration/test_imagine_method_integration.py',
                    'integration/test_full_workflow.py'
                ]
            },
            'e2e': {
                'description': 'End-to-end tests with live APIs (> 5 min, costs credits)',
                'timeout': 600,
                'parallel': False,
                'mock_mode': False,
                'files': [
                    'integration/test_midjourney_live_workflow.py',
                    'integration/test_midjourney_integration.py'
                ],
                'warning': 'These tests use real Midjourney API calls and consume credits!'
            },
            'quick': {
                'description': 'Quickest tests only (< 10s)',
                'timeout': 10,
                'parallel': True,
                'mock_mode': True,
                'files': [
                    'unit/test_error_classes.py',
                    'unit/test_rate_limiter.py',
                    'unit/test_basic.py',
                    'unit/test_prompt_formatting.py'
                ]
            }
        }
        
    def setup_environment(self):
        """Set up test environment and validate configuration"""
        print(f"{Colors.BLUE}=== Setting Up Test Environment ==={Colors.NC}")
        
        # Create required directories
        self.test_output_dir.mkdir(exist_ok=True)
        self.test_logs_dir.mkdir(exist_ok=True)
        
        # Set Python path
        os.environ['PYTHONPATH'] = f"{os.environ.get('PYTHONPATH', '')}:{self.project_root}"
        
        # Change to test directory
        os.chdir(self.script_dir)
        
        print(f"{Colors.GREEN}✓ Environment setup complete{Colors.NC}")
        
    def validate_environment(self, category: str) -> bool:
        """Validate environment for the specified test category"""
        print(f"{Colors.BLUE}=== Validating Environment for {category.title()} Tests ==={Colors.NC}")
        
        # Check if pytest is available
        try:
            result = subprocess.run(['python', '-m', 'pytest', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"{Colors.RED}✖ pytest not available{Colors.NC}")
                return False
        except FileNotFoundError:
            print(f"{Colors.RED}✖ Python not found{Colors.NC}")
            return False
            
        # For live tests, check environment variables
        if not self.test_categories[category]['mock_mode']:
            required_vars = [
                'DISCORD_USER_TOKEN',
                'DISCORD_BOT_TOKEN', 
                'DISCORD_CHANNEL_ID',
                'DISCORD_GUILD_ID'
            ]
            
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            if missing_vars:
                print(f"{Colors.RED}✖ Missing required environment variables: {', '.join(missing_vars)}{Colors.NC}")
                print(f"{Colors.YELLOW}Please set these variables or use --mock-mode{Colors.NC}")
                return False
                
        print(f"{Colors.GREEN}✓ Environment validation passed{Colors.NC}")
        return True
        
    def run_test_file(self, test_file: str, category: str, verbose: bool = False) -> Tuple[bool, str]:
        """Run a single test file and return success status and output"""
        config = self.test_categories[category]
        
        # Build pytest command
        cmd = ['python', '-m', 'pytest', test_file]
        
        if verbose:
            cmd.append('-v')
            
        # Add asyncio mode for integration tests
        if 'integration' in test_file:
            cmd.extend(['--asyncio-mode=strict'])
            
        # Set environment variables based on category
        env = os.environ.copy()
        if config['mock_mode']:
            env['FULLY_MOCKED'] = 'true'
            env['LIVE_TEST'] = 'false'
        else:
            env['FULLY_MOCKED'] = 'false'
            env['LIVE_TEST'] = 'true'
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=config['timeout'], env=env)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Test timed out after {config['timeout']} seconds"
        except Exception as e:
            return False, f"Error running test: {str(e)}"
            
    def run_category(self, category: str, verbose: bool = False, 
                    fail_fast: bool = False) -> Dict:
        """Run all tests in a category"""
        config = self.test_categories[category]
        
        print(f"{Colors.BLUE}=== Running {category.title()} Tests ==={Colors.NC}")
        print(f"{Colors.CYAN}{config['description']}{Colors.NC}")
        
        if 'warning' in config:
            print(f"{Colors.YELLOW}⚠ WARNING: {config['warning']}{Colors.NC}")
            
        results = {
            'category': category,
            'total': len(config['files']),
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'duration': 0,
            'files': {}
        }
        
        start_time = time.time()
        
        for test_file in config['files']:
            file_path = self.script_dir / test_file
            
            if not file_path.exists():
                print(f"{Colors.YELLOW}⚠ Skipping missing file: {test_file}{Colors.NC}")
                results['skipped'] += 1
                results['files'][test_file] = {'status': 'skipped', 'reason': 'File not found'}
                continue
                
            print(f"{Colors.WHITE}• Running {test_file}...{Colors.NC}", end=' ')
            
            file_start = time.time()
            success, output = self.run_test_file(test_file, category, verbose)
            file_duration = time.time() - file_start
            
            if success:
                print(f"{Colors.GREEN}✓ PASSED{Colors.NC} ({file_duration:.1f}s)")
                results['passed'] += 1
                results['files'][test_file] = {
                    'status': 'passed', 
                    'duration': file_duration,
                    'output': output if verbose else ''
                }
            else:
                print(f"{Colors.RED}✖ FAILED{Colors.NC} ({file_duration:.1f}s)")
                results['failed'] += 1
                results['files'][test_file] = {
                    'status': 'failed',
                    'duration': file_duration, 
                    'output': output
                }
                
                if verbose or fail_fast:
                    print(f"{Colors.RED}Error output:{Colors.NC}")
                    print(output)
                    
                if fail_fast:
                    break
                    
        results['duration'] = time.time() - start_time
        return results
        
    def generate_report(self, all_results: List[Dict], output_format: str = 'console'):
        """Generate test report in specified format"""
        if output_format == 'console':
            self._generate_console_report(all_results)
        elif output_format == 'json':
            self._generate_json_report(all_results)
        elif output_format == 'junit':
            self._generate_junit_report(all_results)
            
    def _generate_console_report(self, all_results: List[Dict]):
        """Generate console report"""
        print(f"\n{Colors.BLUE}=== Test Summary ==={Colors.NC}")
        
        total_passed = sum(r['passed'] for r in all_results)
        total_failed = sum(r['failed'] for r in all_results)
        total_skipped = sum(r['skipped'] for r in all_results)
        total_duration = sum(r['duration'] for r in all_results)
        
        for result in all_results:
            status_color = Colors.GREEN if result['failed'] == 0 else Colors.RED
            print(f"{status_color}{result['category'].title():12}{Colors.NC} "
                  f"Passed: {result['passed']:2d} "
                  f"Failed: {result['failed']:2d} "
                  f"Skipped: {result['skipped']:2d} "
                  f"({result['duration']:.1f}s)")
                  
        print(f"\n{Colors.WHITE}Overall Results:{Colors.NC}")
        print(f"  Total Passed:  {total_passed}")
        print(f"  Total Failed:  {total_failed}")
        print(f"  Total Skipped: {total_skipped}")
        print(f"  Total Duration: {total_duration:.1f}s")
        
        if total_failed == 0:
            print(f"\n{Colors.GREEN}🎉 All tests passed!{Colors.NC}")
        else:
            print(f"\n{Colors.RED}❌ {total_failed} test(s) failed{Colors.NC}")
            
    def _generate_json_report(self, all_results: List[Dict]):
        """Generate JSON report"""
        timestamp = datetime.now().isoformat()
        report = {
            'timestamp': timestamp,
            'summary': {
                'total_passed': sum(r['passed'] for r in all_results),
                'total_failed': sum(r['failed'] for r in all_results),
                'total_skipped': sum(r['skipped'] for r in all_results),
                'total_duration': sum(r['duration'] for r in all_results)
            },
            'categories': all_results
        }
        
        output_file = self.test_logs_dir / f"test_results_{timestamp.replace(':', '-')}.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"{Colors.GREEN}JSON report saved to: {output_file}{Colors.NC}")
        
    def confirm_expensive_tests(self, categories: List[str]) -> bool:
        """Ask for confirmation before running expensive tests"""
        expensive_categories = [cat for cat in categories 
                              if not self.test_categories[cat]['mock_mode']]
        
        if not expensive_categories:
            return True
            
        print(f"\n{Colors.RED}⚠ WARNING: The following test categories use real APIs and may cost money:{Colors.NC}")
        for cat in expensive_categories:
            config = self.test_categories[cat]
            print(f"  • {cat}: {config.get('warning', 'Uses live APIs')}")
            
        response = input(f"\n{Colors.YELLOW}Do you want to continue? (y/N): {Colors.NC}")
        return response.lower() in ['y', 'yes']

def main():
    parser = argparse.ArgumentParser(description='Unified test runner for image generator')
    parser.add_argument('--category', '-c', choices=['unit', 'integration', 'e2e', 'quick', 'all'],
                       default='unit', help='Test category to run')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--fail-fast', '-x', action='store_true', 
                       help='Stop on first failure')
    parser.add_argument('--ci', action='store_true',
                       help='CI mode (no confirmations, structured output)')
    parser.add_argument('--format', choices=['console', 'json', 'junit'],
                       default='console', help='Output format')
    parser.add_argument('--mock-mode', action='store_true',
                       help='Force mock mode for all tests')
    parser.add_argument('--list', action='store_true',
                       help='List available test categories and exit')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.list:
        print("Available test categories:")
        for name, config in runner.test_categories.items():
            print(f"  {name:12} - {config['description']}")
        return 0
        
    runner.setup_environment()
    
    # Determine categories to run
    if args.category == 'all':
        categories = ['unit', 'integration', 'e2e']
    else:
        categories = [args.category]
        
    # Override mock mode if requested
    if args.mock_mode:
        for cat in categories:
            runner.test_categories[cat]['mock_mode'] = True
            
    # Confirm expensive tests unless in CI mode
    if not args.ci and not runner.confirm_expensive_tests(categories):
        print("Test execution cancelled.")
        return 1
        
    all_results = []
    
    for category in categories:
        # Validate environment for this category
        if not runner.validate_environment(category):
            print(f"{Colors.RED}Environment validation failed for {category} tests{Colors.NC}")
            return 1
            
        # Run tests for this category
        results = runner.run_category(category, args.verbose, args.fail_fast)
        all_results.append(results)
        
        # Stop if tests failed and fail-fast is enabled
        if args.fail_fast and results['failed'] > 0:
            break
            
    # Generate report
    runner.generate_report(all_results, args.format)
    
    # Return appropriate exit code
    total_failed = sum(r['failed'] for r in all_results)
    return 1 if total_failed > 0 else 0

if __name__ == '__main__':
    sys.exit(main())