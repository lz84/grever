"""Test script for tag_prerequisites"""
from services.tag_prerequisites import (
    validate_prerequisites,
    detect_circular_dependencies,
    resolve_all_prerequisites,
    check_deprecated_tags,
    suggest_replacements,
    CircularDependencyError,
    MaxDepthExceededError,
)

def test_validate_prerequisites_no_missing():
    """chem:msds-parsing has no prerequisites -> {}"""
    result = validate_prerequisites(['chem:msds-parsing'])
    print('Test1 validate_prerequisites chem:msds-parsing:', result)
    assert result == {}, f'FAIL: Expected empty dict, got {result}'
    print('PASS')

def test_validate_prerequisites_with_missing():
    """chem:hazmat-identification needs chem:msds-parsing, which is NOT in input"""
    result = validate_prerequisites(['chem:hazmat-identification'])
    print('Test2 validate_prerequisites chem:hazmat-identification:', result)
    assert 'chem:hazmat-identification' in result, f'FAIL: Expected hazmat-identification key'
    assert 'chem:msds-parsing' in result['chem:hazmat-identification'], f'FAIL: Expected msds-parsing in missing list'
    print('PASS')

def test_validate_prerequisites_all_present():
    """hazmat-identification WITH msds-parsing provided -> no missing"""
    result = validate_prerequisites(['chem:hazmat-identification', 'chem:msds-parsing'])
    print('Test2b validate_prerequisites (both provided):', result)
    assert result == {}, f'FAIL: Expected empty dict when both provided, got {result}'
    print('PASS')

def test_resolve_all_prerequisites():
    """resolve_all_prerequisites for chem:evacuation-planning returns full chain"""
    result = resolve_all_prerequisites(['chem:evacuation-planning'])
    print('Test3 resolve_all_prerequisites chem:evacuation-planning:', result)
    required = {'chem:evacuation-planning', 'chem:diffusion-modeling', 'chem:emergency-response-level', 'chem:hazmat-identification', 'chem:msds-parsing', 'chem:weather-analysis'}
    for tag in required:
        assert tag in result, f'FAIL: Missing tag {tag} in result'
    print('PASS')

def test_detect_circular_simple_no_cycle():
    """detect_circular_dependencies for non-circular tags"""
    result = detect_circular_dependencies(['chem:msds-parsing', 'chem:hazmat-identification'])
    print('Test4 detect_circular (no-cycle):', result)
    assert result == [], f'FAIL: Expected no cycles, got {result}'
    print('PASS')

def test_detect_circular_chain():
    """resolve a chain works (hazmat -> msds) -> no cycle"""
    cycles = detect_circular_dependencies(['chem:evacuation-planning'])
    print('Test4b detect_circular evacuation-planning:', cycles)
    assert cycles == [], f'FAIL: Expected no cycles in evacuation chain, got {cycles}'
    print('PASS')

def test_check_deprecated_tags():
    """check_deprecated_tags works on active tags"""
    result = check_deprecated_tags(['chem:msds-parsing', 'chem:hazmat-identification'])
    print('Test5 check_deprecated_tags (active tags):', result)
    # active tags should not appear in warnings
    for w in result:
        assert w['status'] == 'deprecated' or w['replaced_by'], f'FAIL: Active tags should not be in warnings'
    print('PASS')

def test_suggest_replacements():
    """suggest_replacements returns empty for unknown/non-deprecated tags"""
    result = suggest_replacements(['chem:msds-parsing', 'chem:hazmat-identification'])
    print('Test6 suggest_replacements (active tags):', result)
    assert result == {}, f'FAIL: Expected empty dict for active tags, got {result}'
    print('PASS')

def test_circular_detection_in_db():
    """Test with DB data - check for circular in evacuation-planning chain"""
    cycles = detect_circular_dependencies(['chem:evacuation-planning'])
    print('Test7 detect_circular in evacuation chain:', cycles)
    # No circular in DB data
    assert cycles == [], f'FAIL: Should have no cycles in DB data'
    print('PASS')

if __name__ == '__main__':
    test_validate_prerequisites_no_missing()
    test_validate_prerequisites_with_missing()
    test_validate_prerequisites_all_present()
    test_resolve_all_prerequisites()
    test_detect_circular_simple_no_cycle()
    test_detect_circular_chain()
    test_check_deprecated_tags()
    test_suggest_replacements()
    test_circular_detection_in_db()
    print()
    print('All tests PASSED')
