import pytest

import ankiconnect_wrapper
from .. import ankikindle
from unittest.mock import Mock


def test_build_notes():
    notes = [{'annotationId': 'ABCDEFGH1234',
              'highlight': '狐につままれ',
              'location': {'value': 4, 'type': 'page'},
              'sentence': '若槻は狐につままれたような面持ちで確認した。',
              'note': ''}]
    expected_notes = [{'sentence': '若槻は狐につままれたような面持ちで確認した。', 'word': '狐につままれ'}]
    assert ankikindle.build_notes(notes) == expected_notes


def test_ankiconnect_request_permission_permission_denied():
    ankiconnect_wrapper_mock = Mock()
    ankiconnect_wrapper_mock.request_connection_permission.return_value = {'permission': 'denied'}
    with pytest.raises(Exception) as e:
        ankikindle.ankiconnect_request_permission(ankiconnect_wrapper_mock)
    assert str(e.value) == "Failed to authenticate with Anki; response: {'permission': 'denied'}"


def test_add_notes_to_anki_mocked_no_duplicate_found():
    ankiconnect_wrapper_mock = Mock()
    ankiconnect_wrapper_mock.request_connection_permission.return_value = {'permission': 'granted'}
    ankiconnect_wrapper_mock.get_all_deck_names.return_value = ['Default']
    ankiconnect_wrapper_mock.get_all_card_type_names.return_value = ['Basic']
    ankiconnect_wrapper_mock.get_anki_note_ids_from_query.return_value = []
    ankiconnect_wrapper_mock.add_anki_note.return_value = 101

    notes = [{'sentence': 'This is a test sentence', 'word': 'test'}]
    deck_name = 'Default'
    model_name = 'Basic'

    result_note_ids = ankikindle.add_notes_to_anki(notes, deck_name, model_name, ankiconnect_wrapper_mock)
    assert result_note_ids == [101]


def test_update_note_with_more_examples_mocked():
    ankiconnect_wrapper_mock = Mock()
    mocked_return_value = {'noteId': 101,
                           'modelName': 'Basic',
                           'deckName': 'Default',
                           'tags': ['1'],
                           'fields': {
                               'Furigana': 'test',
                               'Expression': 'This is a test sentence',
                               'Sentence': 'example1',
                               'Meaning': '',
                               'Pronunciation': ''
                           }
                           }  # notesInfo for first note
    ankiconnect_wrapper_mock.get_single_anki_note_details.return_value = mocked_return_value
    ankiconnect_wrapper_mock.get_decks_containing_card.return_value = ['Default']
    ankiconnect_wrapper_mock.update_anki_note.return_value = None
    ankikindle.update_note_with_more_examples(101, 'example2', ankiconnect_wrapper_mock)

    expected_fields = {
        'Furigana': 'test',
        'Expression': 'This is a test sentence',
        'Sentence': 'example2' + '</br>' + 'example1',
        'Meaning': '',
        'Pronunciation': ''
    }
    ankiconnect_wrapper_mock.update_anki_note.assert_called_once_with(101, expected_fields, '2')


def test_check_and_update_example_sentences():
    more_examples = ''
    new_example = 'Example 1.'
    expected_output = 'Example 1.</br>'
    assert ankikindle._check_and_update_example_sentences(more_examples, new_example) == expected_output

    more_examples = 'Example 2.</br>Example 1.'
    new_example = 'Example 3.'
    expected_output = 'Example 3.</br>Example 2.</br>Example 1.'
    assert ankikindle._check_and_update_example_sentences(more_examples, new_example) == expected_output

    more_examples = 'Example 3.</br>Example 2.</br>Example 1.'
    new_example = 'Example 4.'
    expected_output = 'Example 4.</br>Example 3.</br>Example 2.'
    assert ankikindle._check_and_update_example_sentences(more_examples, new_example) == expected_output


def test_add_update_and_remove_notes_to_anki():
    deck_name = 'mail_sucks_in_japan'
    model_name = 'aedict'
    notes = [
        {'sentence': '若槻は狐につままれたような面持ちで確認した。', 'word': '狐につままれ'}
    ]
    added_note_ids = ankikindle.add_notes_to_anki(notes, deck_name, model_name, ankiconnect_wrapper)

    all_note_ids_of_deck_that_was_added_to = ankiconnect_wrapper.get_anki_note_ids_from_query(f'deck:{deck_name}')
    for note_id in added_note_ids:
        assert note_id in all_note_ids_of_deck_that_was_added_to

    new_example = '狐につままれの新しい例文'
    note_to_be_updated = added_note_ids[0]
    ankikindle.update_note_with_more_examples(note_to_be_updated, new_example, ankiconnect_wrapper)

    updated_note = ankiconnect_wrapper.get_single_anki_note_details(note_to_be_updated, True)
    assert new_example in updated_note['fields']['Sentence']
    assert updated_note['tags'][0] == '2'

    added_and_updated_note_id = updated_note['noteId']
    ankikindle.remove_notes_from_anki(updated_note['noteId'], ankiconnect_wrapper)
    note_ids_after_deletion = ankiconnect_wrapper.get_anki_note_ids_from_query(f'deck:"{deck_name}"')
    assert added_and_updated_note_id not in note_ids_after_deletion
