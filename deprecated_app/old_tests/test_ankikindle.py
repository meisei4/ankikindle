import pytest
import threading
from ..old_src import vocab_db_accessor_wrap, ankikindle
from ..old_src import ankiconnect_wrapper
from sqlite3 import Connection
from unittest.mock import Mock
from .test_util import add_word_lookups_to_db_for_non_main_thread, get_test_temp_db_file_name


def test_update_database_while_main_program_is_running(db_connection: Connection, temp_db_directory: str):
    ankiconnect_wrapper_mock = Mock()
    ankiconnect_wrapper_mock.request_connection_permission.return_value = {'permission': 'granted'}
    ankiconnect_wrapper_mock.get_all_deck_names.return_value = ['mail_sucks_in_japan']
    ankiconnect_wrapper_mock.get_all_card_type_names.return_value = ['aedict']
    ankiconnect_wrapper_mock.get_anki_note_id_from_query.return_value = -1

    db_update_ready_event = threading.Event()
    db_update_processed_event = threading.Event()
    main_thread_stop_event = threading.Event()
    temp_db_file_path = get_test_temp_db_file_name(temp_db_directory)
    db_update_thread = threading.Thread(target=add_word_lookups_to_db_for_non_main_thread,
                                        args=(temp_db_file_path,
                                              db_update_ready_event,
                                              db_update_processed_event,
                                              main_thread_stop_event))
    db_update_thread.start()

    ankikindle_main_function_wrapper(db_connection,
                                     ankiconnect_wrapper_mock,
                                     db_update_ready_event,
                                     db_update_processed_event,
                                     main_thread_stop_event)

    db_update_thread.join()

    word_lookups_after_timestamp = vocab_db_accessor_wrap.get_word_lookups_after_timestamp(db_connection,
                                                                                           ankikindle.DEFAULT_TIMESTAMP)
    assert len(word_lookups_after_timestamp) == 1
    assert word_lookups_after_timestamp[0]["word"] == "日本語"
    assert word_lookups_after_timestamp[0]["usage"] == "日本語の例文"
    assert word_lookups_after_timestamp[0]["title"] == "日本の本"
    assert word_lookups_after_timestamp[0]["authors"] == "著者A"

    expected_note = {'deckName': 'mail_sucks_in_japan',
                     'modelName': 'aedict',
                     'tags': ['1'],
                     'fields': {
                         'Expression': '日本語の例文',
                         'Furigana': '日本語',
                         'Sentence': '日本語の例文'}
                     }
    ankiconnect_wrapper_mock.add_anki_note.assert_called_once_with(expected_note)


def ankikindle_main_function_wrapper(connection_injection: Connection, ankiconnect_injection: ankiconnect_wrapper,
                                     db_update_ready_event: threading.Event,
                                     db_update_processed_event: threading.Event,
                                     stop_event: threading.Event):
    while not stop_event.is_set():
        processed_new_vocab_highlights = ankikindle.process_new_vocab_highlights(connection_injection,
                                                                                 ankiconnect_injection)
        if processed_new_vocab_highlights:
            db_update_processed_event.set()

        db_update_ready_event.set()


def test_ankiconnect_request_permission_permission_denied():
    ankiconnect_wrapper_mock = Mock()
    ankiconnect_wrapper_mock.request_connection_permission.return_value = {'permission': 'denied'}
    with pytest.raises(Exception) as e:
        ankikindle.ankiconnect_request_permission(ankiconnect_wrapper_mock)
    assert str(e.value) == "failed to authenticate with anki; response: {'permission': 'denied'}"


def test_add_notes_to_anki_mocked_no_duplicate_found():
    ankiconnect_wrapper_mock = Mock()
    ankiconnect_wrapper_mock.request_connection_permission.return_value = {'permission': 'granted'}
    ankiconnect_wrapper_mock.get_all_deck_names.return_value = ['Default']
    ankiconnect_wrapper_mock.get_all_card_type_names.return_value = ['Basic']
    ankiconnect_wrapper_mock.get_anki_note_id_from_query.return_value = -1
    ankiconnect_wrapper_mock.add_anki_note.return_value = 101

    word_highlights = [{'usage': 'This is a test sentence', 'word': 'test'}]
    deck_name = 'Default'
    model_name = 'Basic'

    result_note_ids = ankikindle.add_notes_to_anki(word_highlights, deck_name, model_name, ankiconnect_wrapper_mock)
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
    ankiconnect_wrapper_mock.update_anki_note.assert_called_once_with(101, expected_fields, 2)


def test_update_example_sentences():
    example_sentences = ''
    new_example = 'Example 1.'
    expected_output = 'Example 1.</br>'
    assert ankikindle._update_example_sentences(example_sentences, new_example) == expected_output

    example_sentences = 'Example 2.</br>Example 1.'
    new_example = 'Example 3.'
    expected_output = 'Example 3.</br>Example 2.</br>Example 1.'
    assert ankikindle._update_example_sentences(example_sentences, new_example) == expected_output

    example_sentences = 'Example 3.</br>Example 2.</br>Example 1.'
    new_example = 'Example 4.'
    expected_output = 'Example 4.</br>Example 3.</br>Example 2.'
    assert ankikindle._update_example_sentences(example_sentences, new_example) == expected_output


def test_add_update_and_remove_notes_to_anki():
    deck_name = 'mail_sucks_in_japan'
    model_name = 'aedict'
    notes = [
        {'usage': '若槻は狐につままれたような面持ちで確認した。', 'word': '狐につままれ'}
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
