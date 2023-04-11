import logging
import requests
import ankisync2.ankiconnect

# ankiconnect actions
ADD_NOTE = 'addNote'
DELETE_NOTES = 'deleteNotes'
# TODO figure out how findNotes return type looks
FIND_NOTES = 'findNotes'
DECK_NAMES = 'deckNames'
MODEL_NAMES = 'modelNames'

# dict keys
NOTES = 'notes'
SENTENCE = 'sentence'
WORD = 'word'

# Replace <YOUR_AUTHORIZATION_HEADER> with the value you copied from the "Authorization" header in the developer tools.
logger = logging.getLogger(__name__)


def main(anki_connect_injection):
    deck_name = ""
    model_name = ""

    # TODO get header and actually have this response thing work
    headers = ""
    response = requests.get(f'https://kindle.amazon.com/kp/kindle-dbs/notes/2010-05-01/<YOUR_TITLE>', headers=headers)
    clippings_json = response.json()
    clippings = parse_clippings(clippings_json)
    for clipping in clippings:
        anki_notes = build_notes(clipping[NOTES])
        add_notes_to_anki(anki_notes, deck_name, model_name, anki_connect_injection)


def parse_clippings(clippings_json):
    clippings = []
    for clipping in clippings_json:
        clippings.append({
            'asin': clipping['asin'],
            'lastUpdatedDate': clipping['lastUpdatedDate'],
            'authors': clipping['authors'],
            'title': clipping['title'],
            NOTES: clipping[NOTES]
        })
    return clippings


def build_notes(notes_dict):
    anki_notes = []
    for note in notes_dict:
        anki_note = build_single_note(note)
        anki_notes.append(anki_note)
    return anki_notes


def build_single_note(note_contents):
    sentence = note_contents[SENTENCE]
    word = note_contents['highlight']
    return {SENTENCE: sentence, WORD: word}


def add_notes_to_anki(clipping_notes, deck_name, model_name, anki_connect_injection):
    ankiconnect_request_permission(anki_connect_injection)
    confirm_existence_of_ankiconnect_item_by_name(DECK_NAMES, deck_name, anki_connect_injection)
    confirm_existence_of_ankiconnect_item_by_name(MODEL_NAMES, model_name, anki_connect_injection)
    added_note_ids = []
    for clipping_note in clipping_notes:
        note_id = add_or_update_note(clipping_note, deck_name, model_name, anki_connect_injection)
        added_note_ids.append(note_id)
    return added_note_ids


def add_or_update_note(clipping_note, deck_name, model_name, anki_connect_injection):
    query = 'deck:"{}" "Furigana:{}"'.format(deck_name, clipping_note[WORD])
    existing_notes = anki_connect_injection(FIND_NOTES, query=query)
    if len(existing_notes) >= 1:
        update_note_with_more_examples(existing_notes[0], clipping_note[SENTENCE], anki_connect_injection)
        return existing_notes[0]

    return add_new_note(clipping_note, deck_name, model_name, anki_connect_injection)


def update_note_with_more_examples(note_id, new_example, anki_connect_injection):
    # TODO figure out how notesInfo return type looks
    note = anki_connect_injection('notesInfo', notes=[note_id])[0]
    more_examples = note['Example Sentence']
    more_examples += '<br/>' + new_example
    fields = {'Example Sentence': more_examples}
    update_counter(note_id, anki_connect_injection)
    anki_connect_injection('updateNoteFields', note={'id': note_id, 'fields': fields})


def update_counter(note_id, anki_connect_injection):
    note = anki_connect_injection('notesInfo', notes=[note_id])[0]
    counter = int(note['Counter'])
    counter += 1
    note['Counter'] = str(counter)
    if counter >= 3:
        note['deckName'] = 'Priority Words'
    anki_connect_injection('updateNoteFields', note=note)


def add_new_note(clipping_note, deck_name, model_name, anki_connect_injection):
    fields = {
        'Expression': clipping_note[SENTENCE],
        'Furigana': clipping_note[WORD],
        'Example Sentence': clipping_note[SENTENCE],
        'Counter': 1
    }
    anki_note = {'deckName': deck_name, 'modelName': model_name, 'fields': fields}
    return anki_connect_injection(ADD_NOTE, note=anki_note)


def ankiconnect_request_permission(anki_connect_injection):
    anki_conn = anki_connect_injection('requestPermission')
    if not anki_conn['permission'] == 'granted':
        raise Exception(f"Failed to authenticate with Anki; response: {anki_conn}")


def confirm_existence_of_ankiconnect_item_by_name(action, target_item, anki_connect_injection):
    items = anki_connect_injection(f'{action}')
    if target_item not in items:
        raise Exception(f"{action} '{target_item}' not found in remote Anki account")
    return True


# TODO only for recovery during unmocked connection testing purposes (adding unwanted cards). move somewhere else or
#  figure out it being needed later
def remove_notes_from_anki(note_ids_to_be_removed, anki_connect_injection):
    ankiconnect_request_permission(anki_connect_injection)
    notes_to_delete = ankisync2.ankiconnect(FIND_NOTES,
                                            query=f"nid:{','.join(str(n) for n in note_ids_to_be_removed)}")
    ankisync2.ankiconnect(DELETE_NOTES, notes=notes_to_delete)
