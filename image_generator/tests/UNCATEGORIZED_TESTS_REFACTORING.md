# Uncategorized Tests Refactoring Plan

## Current State Analysis

### Files to Refactor
1. **`test_upscale_correlation.py`** (222 lines) - ✅ Already proper pytest
2. **`test_imagine_command_details.py`** (115 lines) - ❌ Standalone script  
3. **`test_imagine_from_generate_image.py`** (112 lines) - ❌ Standalone script
4. **`test_generate_and_upscale.py`** (124 lines) - ❌ Standalone script

## Refactoring Strategy

### 1. `test_upscale_correlation.py` → `integration/test_upscale_correlation_duplicate.py`
**Status**: ✅ Already proper pytest format
**Action**: Move to integration directory (duplicate of existing integration test)
**Issue**: This appears to be a duplicate of `integration/test_upscale_correlation.py`
**Resolution**: Compare files and consolidate or differentiate

### 2. `test_imagine_command_details.py` → `integration/test_imagine_command_details.py`
**Purpose**: Tests Discord slash command payload structure
**Refactoring needed**:
- Convert from standalone script to pytest format
- Add proper fixtures and test methods
- Mock external dependencies appropriately
- Category: **Integration** (tests API call structure)

### 3. `test_imagine_from_generate_image.py` → `integration/test_imagine_method_integration.py`
**Purpose**: Tests integration between high-level API and slash commands
**Refactoring needed**:
- Convert from standalone script to pytest format
- Add proper test class and methods
- Use existing fixtures
- Category: **Integration** (tests method chaining)

### 4. `test_generate_and_upscale.py` → `integration/test_full_workflow.py`
**Purpose**: Tests complete generate→upscale workflow
**Refactoring needed**:
- Convert from standalone script to pytest format  
- Break down into multiple test methods
- Add proper assertions and error handling
- Category: **Integration** (tests full workflow)

## Implementation Plan

### Phase 1: Analysis and Deduplication
- [ ] Compare `test_upscale_correlation.py` with `integration/test_upscale_correlation.py`
- [ ] Determine if they test different aspects or are true duplicates
- [ ] Consolidate or differentiate as needed

### Phase 2: Convert Standalone Scripts
- [ ] Refactor `test_imagine_command_details.py` to pytest format
- [ ] Refactor `test_imagine_from_generate_image.py` to pytest format  
- [ ] Refactor `test_generate_and_upscale.py` to pytest format

### Phase 3: Integration and Testing
- [ ] Move refactored tests to `integration/` directory
- [ ] Update test runner configuration
- [ ] Verify all tests pass
- [ ] Update documentation

## Expected Outcomes

### Before Refactoring
```
UNCATEGORIZED TESTS (4 files):
  ❌ test_imagine_command_details.py (standalone script)
  ❌ test_imagine_from_generate_image.py (standalone script)  
  ❌ test_upscale_correlation.py (pytest, wrong location)
  ❌ test_generate_and_upscale.py (standalone script)
```

### After Refactoring  
```
INTEGRATION TESTS (+3 new files):
  ✅ integration/test_imagine_command_details.py
  ✅ integration/test_imagine_method_integration.py
  ✅ integration/test_full_workflow.py
  ✅ integration/test_upscale_correlation.py (consolidated)

UNCATEGORIZED TESTS (0 files):
  🎉 All tests properly categorized!
```

## Benefits

1. **Consistent testing approach**: All tests use pytest framework
2. **Better organization**: Tests in appropriate categories
3. **CI/CD integration**: All tests can run through unified test runner
4. **Maintainability**: Standard pytest patterns for easier maintenance
5. **Better coverage reporting**: Integrated with existing test infrastructure