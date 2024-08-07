import requests

from app.app import logger


class AnkiService:
    # TODO: refs github issue #3 getting the env variable here doesnt work still... i dont know how to fix it
    # ANKI_API_URL = os.getenv("ANKI_API_URL")
    ANKI_API_URL = "http://localhost:8765"
    HEADERS = {"Content-Type": "application/json"}
    VERSION = 6  # Defaulting to 6 as a safe fallback

    @classmethod
    def send_request(cls, action, params=None) -> dict:
        payload = {"action": action, "version": cls.VERSION, "params": params or {}}
        try:
            response = requests.post(cls.ANKI_API_URL, json=payload, headers=cls.HEADERS)
            response_data = response.json()
            logger.info(f"AnkiConnect {action}: {response_data}")
            return response_data
        except requests.RequestException as e:
            logger.error(f"AnkiConnect {action} error: {e}")
            return {"error": str(e)}

    @classmethod
    def request_permission(cls):
        return cls.send_request("requestPermission")

    @classmethod
    def create_deck(cls, deck_name):
        return cls.send_request("createDeck", {"deck": deck_name})

    @classmethod
    def get_all_deck_names(cls):
        return cls.send_request("deckNames").get("result", [])

    @classmethod
    def get_all_model_names(cls):
        return cls.send_request("modelNames").get("result", [])

    @classmethod
    def find_notes(cls, query):
        return cls.send_request("findNotes", {"query": query}).get("result", [])

    @classmethod
    def get_notes_info(cls, note_ids):
        return cls.send_request("notesInfo", {"notes": note_ids}).get("result", [])

    @classmethod
    def add_anki_note(cls, deck_name, model_name, front, back, tags=None):
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {"Front": front, "Back": back},
            "tags": tags or [],
        }
        return cls.send_request("addNote", {"note": note}).get("result")

    @classmethod
    def update_note_fields(cls, note_id, fields):
        note = {"id": note_id, "fields": fields}
        return cls.send_request("updateNoteFields", {"note": note}).get("result")

    @classmethod
    def add_notes_to_anki(cls, vocab_highlights, deck_name, model_name):
        logger.info("Adding notes to Anki...")
        try:
            cls.request_permission()
            if deck_name not in cls.get_all_deck_names():
                raise ValueError(f"Deck named: '{deck_name}' was not found in local Anki account")
            if model_name not in cls.get_all_model_names():
                raise ValueError(f"Card type: '{model_name}' was not found in local Anki account")

            added_note_ids = []
            for highlight in vocab_highlights:
                note_id = cls.add_or_update_note(
                    highlight.word.word, highlight.usage, deck_name, model_name)
                added_note_ids.append(note_id)
                logger.info(f"Added note for word '{highlight.word.word}' with Note ID: {note_id}")

            logger.info(f"Successfully added {len(added_note_ids)} notes to Anki.")
            return added_note_ids
        except ValueError as e:
            logger.error(f"ValueError: {e}")
        except ConnectionError as e:
            logger.error(f"ConnectionError: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    @classmethod
    def add_or_update_note(cls, word, usage, deck_name, model_name):
        existing_note_id = cls.find_existing_note_id(word, deck_name)
        if existing_note_id:
            logger.info(f"Note already exists for '{word}' in '{deck_name}'; updating note")
            cls.update_note_with_more_examples(existing_note_id, usage)
            logger.info("Note updated successfully")
            return existing_note_id
        else:
            logger.info(f"No existing note found for '{word}' in '{deck_name}'; adding new note")
            return cls.add_new_note(
                word, usage, deck_name, model_name)

    @classmethod
    def find_existing_note_id(cls, word, deck_name):
        query = f"deck:'{deck_name}' 'Furigana:{word}'"
        note_ids = cls.find_notes(query)
        return note_ids[0] if note_ids else None

    @classmethod
    def update_note_with_more_examples(cls, note_id, new_example):
        logger.info(f"Updating note with ID {note_id} by adding new example: '{new_example}'")
        note = cls.get_notes_info([note_id])[0]
        note_fields = note['fields']
        example_sentences = note_fields['Sentence']
        updated_example_sentences = cls._update_example_sentences(example_sentences, new_example)
        note_fields['Sentence'] = updated_example_sentences
        cls.update_note_fields(note_id, note_fields)
        logger.info(f"Updated example sentences: '{updated_example_sentences}'")

    @staticmethod
    def _update_example_sentences(example_sentences, new_example):
        example_sentence_list = example_sentences.split('</br>')
        example_sentence_list.insert(0, new_example)
        if len(example_sentence_list) > 3:
            example_sentence_list.pop()
        return '</br>'.join(example_sentence_list)

    @classmethod
    def add_new_note(cls, word, usage, deck_name, model_name):
        fields = {
            'Expression': usage,
            'Furigana': word,
            'Sentence': usage
        }
        return cls.add_anki_note(deck_name, model_name, word, usage, ["vocab"])

    @classmethod
    def delete_notes(cls, note_ids):
        return cls.send_request("deleteNotes", {"notes": note_ids})
