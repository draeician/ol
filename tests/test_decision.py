"""Tests for decision mode functionality."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from ol.decision import (
    load_profile,
    validate_profile,
    find_profile_path,
    list_available_profiles,
    create_inline_boolean_profile,
    check_model_capabilities,
    make_decision_request,
    interpret_noul_result,
    format_decision_output,
    ProfileError,
    CapabilityError,
    DecisionError,
    PROFILE_VERSION,
)


@pytest.fixture
def temp_profile_dir(tmp_path, monkeypatch):
    """Create temporary profile directory."""
    profile_dir = tmp_path / 'decisions'
    profile_dir.mkdir()
    monkeypatch.setattr('ol.decision.get_user_profiles_dir', lambda: profile_dir)
    return profile_dir


def test_validate_profile_valid():
    """Test validating a valid profile."""
    profile = {
        'version': 1,
        'description': 'Test profile',
        'questions': {
            'test': {
                'type': 'noul',
                'instructions': 'Test question',
                'criteria': {
                    'true': 'Yes',
                    'false': 'No'
                }
            }
        }
    }
    validate_profile(profile, 'test')


def test_validate_profile_wrong_version():
    """Test validating profile with wrong version."""
    profile = {
        'version': 999,
        'description': 'Test',
        'questions': {}
    }
    with pytest.raises(ProfileError, match='unsupported version'):
        validate_profile(profile, 'test')


def test_validate_profile_missing_description():
    """Test validating profile without description."""
    profile = {
        'version': 1,
        'questions': {}
    }
    with pytest.raises(ProfileError, match='missing required field'):
        validate_profile(profile, 'test')


def test_validate_profile_invalid_question_type():
    """Test validating profile with invalid question type."""
    profile = {
        'version': 1,
        'description': 'Test',
        'questions': {
            'test': {
                'type': 'invalid',
                'criteria': {}
            }
        }
    }
    with pytest.raises(ProfileError, match='invalid type'):
        validate_profile(profile, 'test')


def test_validate_profile_wrong_criteria_count():
    """Test validating profile with wrong criteria count."""
    profile = {
        'version': 1,
        'description': 'Test',
        'questions': {
            'test': {
                'type': 'noul',
                'criteria': {
                    'true': 'Yes'
                    # Missing 'false'
                }
            }
        }
    }
    with pytest.raises(ProfileError, match='requires 2-2 criteria'):
        validate_profile(profile, 'test')


def test_validate_profile_too_many_questions():
    """Test validating profile with too many questions."""
    questions = {f'q{i}': {'type': 'noul', 'criteria': {'true': 'Y', 'false': 'N'}} 
                 for i in range(65)}
    profile = {
        'version': 1,
        'description': 'Test',
        'questions': questions
    }
    with pytest.raises(ProfileError, match='must have 1-64 questions'):
        validate_profile(profile, 'test')


def test_validate_profile_invalid_thresholds():
    """Test validating profile with invalid noul thresholds."""
    profile = {
        'version': 1,
        'description': 'Test',
        'questions': {
            'test': {
                'type': 'noul',
                'criteria': {'true': 'Y', 'false': 'N'}
            }
        },
        'results': {
            'test': {
                'negative_below': 0.8,
                'positive_at_or_above': 0.2,  # Invalid: should be > negative_below
                'labels': {}
            }
        }
    }
    with pytest.raises(ProfileError, match='must satisfy'):
        validate_profile(profile, 'test')


def test_load_profile_not_found():
    """Test loading non-existent profile."""
    with pytest.raises(ProfileError, match='not found'):
        load_profile('nonexistent')


def test_load_profile_valid_yaml(temp_profile_dir):
    """Test loading valid YAML profile."""
    profile_data = {
        'version': 1,
        'description': 'Test profile',
        'questions': {
            'test': {
                'type': 'noul',
                'criteria': {'true': 'Yes', 'false': 'No'}
            }
        }
    }
    
    profile_path = temp_profile_dir / 'test.yaml'
    with open(profile_path, 'w') as f:
        yaml.safe_dump(profile_data, f)
    
    loaded = load_profile('test')
    assert loaded['version'] == 1
    assert loaded['description'] == 'Test profile'


def test_load_profile_valid_json(temp_profile_dir):
    """Test loading valid JSON profile."""
    profile_data = {
        'version': 1,
        'description': 'Test profile',
        'questions': {
            'test': {
                'type': 'choice',
                'criteria': {'a': 'A', 'b': 'B', 'c': 'C'}
            }
        }
    }
    
    profile_path = temp_profile_dir / 'test.json'
    with open(profile_path, 'w') as f:
        json.dump(profile_data, f)
    
    loaded = load_profile('test')
    assert loaded['version'] == 1


def test_list_available_profiles(temp_profile_dir):
    """Test listing available profiles."""
    # Create some profiles
    for i in range(3):
        profile_data = {
            'version': 1,
            'description': f'Test profile {i}',
            'questions': {
                'test': {
                    'type': 'noul',
                    'criteria': {'true': 'Y', 'false': 'N'}
                }
            }
        }
        with open(temp_profile_dir / f'test{i}.yaml', 'w') as f:
            yaml.safe_dump(profile_data, f)
    
    profiles = list_available_profiles()
    assert len(profiles) >= 3
    names = [name for name, _, _ in profiles]
    assert 'test0' in names
    assert 'test1' in names
    assert 'test2' in names


def test_create_inline_boolean_profile():
    """Test creating inline boolean profile."""
    question = "Is this image blurry?"
    profile = create_inline_boolean_profile(question)
    
    assert profile['version'] == PROFILE_VERSION
    assert 'questions' in profile
    assert 'answer' in profile['questions']
    assert profile['questions']['answer']['type'] == 'noul'
    assert profile['questions']['answer']['instructions'] == question


def test_check_model_capabilities_missing_decision():
    """Test checking capabilities when decision is missing."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'capabilities': ['vision']  # Missing 'decision'
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(CapabilityError, match='does not support System One'):
            check_model_capabilities('http://localhost:11434', 'test-model', False)


def test_check_model_capabilities_missing_vision():
    """Test checking capabilities when vision is missing but required."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'capabilities': ['decision']  # Missing 'vision'
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(CapabilityError, match='does not support vision'):
            check_model_capabilities('http://localhost:11434', 'test-model', True)


def test_check_model_capabilities_valid():
    """Test checking capabilities when all required are present."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'capabilities': ['decision', 'vision']
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch('requests.post', return_value=mock_response):
        # Should not raise
        check_model_capabilities('http://localhost:11434', 'test-model', True)


def test_make_decision_request_success():
    """Test making a successful decision request."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'model': 'tev1',
        'answers': {
            'test': {
                'probability': 0.95
            }
        }
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch('requests.post', return_value=mock_response):
        result = make_decision_request(
            'http://localhost:11434',
            'tev1',
            'Test state',
            {'test': {'type': 'noul', 'criteria': {'true': 'Y', 'false': 'N'}}}
        )
        
        assert 'answers' in result
        assert 'test' in result['answers']


def test_make_decision_request_404_missing_model():
    """Test decision request when model not found."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {'error': 'model not found'}
    
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(DecisionError, match='not found'):
            make_decision_request(
                'http://localhost:11434',
                'missing-model',
                'Test',
                {}
            )


def test_make_decision_request_413():
    """Test decision request when payload too large."""
    mock_response = MagicMock()
    mock_response.status_code = 413
    mock_response.raise_for_status.side_effect = Exception()
    
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(DecisionError, match='too large'):
            make_decision_request(
                'http://localhost:11434',
                'tev1',
                'Test',
                {}
            )


def test_interpret_noul_result_negative():
    """Test interpreting noul result as negative."""
    thresholds = {
        'negative_below': 0.20,
        'positive_at_or_above': 0.80,
        'labels': {
            'negative': 'SFW',
            'uncertain': 'REVIEW',
            'positive': 'NSFW'
        }
    }
    
    category, label = interpret_noul_result(0.15, thresholds)
    assert category == 'negative'
    assert label == 'SFW'


def test_interpret_noul_result_uncertain():
    """Test interpreting noul result as uncertain."""
    thresholds = {
        'negative_below': 0.20,
        'positive_at_or_above': 0.80,
        'labels': {
            'negative': 'SFW',
            'uncertain': 'REVIEW',
            'positive': 'NSFW'
        }
    }
    
    category, label = interpret_noul_result(0.50, thresholds)
    assert category == 'uncertain'
    assert label == 'REVIEW'


def test_interpret_noul_result_positive():
    """Test interpreting noul result as positive."""
    thresholds = {
        'negative_below': 0.20,
        'positive_at_or_above': 0.80,
        'labels': {
            'negative': 'SFW',
            'uncertain': 'REVIEW',
            'positive': 'NSFW'
        }
    }
    
    category, label = interpret_noul_result(0.95, thresholds)
    assert category == 'positive'
    assert label == 'NSFW'


def test_format_decision_output_human():
    """Test formatting decision output for humans."""
    response = {
        'model': 'tev1',
        'answers': {
            'nsfw': {
                'probability': 0.95
            }
        }
    }
    
    profile = {
        'questions': {
            'nsfw': {
                'type': 'noul',
                'criteria': {'true': 'NSFW', 'false': 'SFW'}
            }
        },
        'results': {
            'nsfw': {
                'negative_below': 0.20,
                'positive_at_or_above': 0.80,
                'labels': {
                    'negative': 'SFW',
                    'uncertain': 'REVIEW',
                    'positive': 'NSFW'
                }
            }
        }
    }
    
    output = format_decision_output(response, profile, source='test.jpg')
    assert 'NSFW' in output
    assert 'test.jpg' in output
    assert '0.95' in output


def test_format_decision_output_json():
    """Test formatting decision output as JSON."""
    response = {
        'model': 'tev1',
        'answers': {
            'test': {
                'probability': 0.50
            }
        }
    }
    
    profile = {
        'questions': {
            'test': {
                'type': 'noul',
                'criteria': {'true': 'Y', 'false': 'N'}
            }
        },
        'results': {
            'test': {
                'negative_below': 0.20,
                'positive_at_or_above': 0.80,
                'labels': {
                    'negative': 'NO',
                    'uncertain': 'MAYBE',
                    'positive': 'YES'
                }
            }
        }
    }
    
    output = format_decision_output(response, profile, json_output=True)
    parsed = json.loads(output)
    
    assert parsed['status'] == 'success'
    assert parsed['model'] == 'tev1'
    assert 'results' in parsed
    assert 'test' in parsed['results']
    assert parsed['results']['test']['category'] == 'uncertain'
    assert parsed['results']['test']['label'] == 'MAYBE'


def test_format_decision_output_choice():
    """Test formatting choice question output."""
    response = {
        'model': 'clef-flash',
        'answers': {
            'egg_count': {
                'value': '6',
                'probabilities': {'6': 0.95, '7': 0.03, '5': 0.02}
            }
        }
    }
    
    profile = {
        'questions': {
            'egg_count': {
                'type': 'choice',
                'criteria': {str(i): None for i in range(13)}
            }
        }
    }
    
    output = format_decision_output(response, profile, source='eggs.jpg')
    assert '6' in output
    assert 'eggs.jpg' in output


def test_bundled_profiles_exist():
    """Test that bundled profiles exist and are valid."""
    from ol.decision import get_bundled_profiles_dir
    
    bundled_dir = get_bundled_profiles_dir()
    assert bundled_dir.exists()
    
    # Check nsfw profile
    nsfw_path = bundled_dir / 'nsfw.yaml'
    assert nsfw_path.exists()
    
    with open(nsfw_path) as f:
        nsfw_profile = yaml.safe_load(f)
    
    validate_profile(nsfw_profile, 'nsfw')
    assert nsfw_profile['version'] == 1
    assert 'nsfw' in nsfw_profile['questions']
    
    # Check eggs profile
    eggs_path = bundled_dir / 'eggs.yaml'
    assert eggs_path.exists()
    
    with open(eggs_path) as f:
        eggs_profile = yaml.safe_load(f)
    
    validate_profile(eggs_profile, 'eggs')
    assert eggs_profile['version'] == 1
    assert 'egg_count' in eggs_profile['questions']
