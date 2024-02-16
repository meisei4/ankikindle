import pytest
from datetime import datetime
from app import db
from app.models.models import Word, BookInfo, Lookup
from app_tests.conftest import logger


# Assuming logging is already configured

@pytest.mark.usefixtures('test_app')
class TestDatabaseOperations:
    def test_insert_word_and_lookup(self, init_database):
        logger.info("Starting test: test_insert_word_and_lookup")

        # Create new word and book info
        logger.info("Inserting new Word and BookInfo into the database")
        new_word = Word(word='Python')
        new_book_info = BookInfo(title='Learn Python Programming', authors='John Doe')
        init_database.session.add(new_word)
        init_database.session.add(new_book_info)
        init_database.session.commit()

        logger.info("Verifying insertion")
        assert Word.query.count() == 1, "Word count mismatch"
        assert BookInfo.query.count() == 1, "BookInfo count mismatch"

        # Create a new lookup
        logger.info("Inserting new Lookup into the database")
        timestamp = int(datetime.now().timestamp())
        new_lookup = Lookup(word=new_word, book_info=new_book_info, usage='Python is great!', timestamp=timestamp)
        init_database.session.add(new_lookup)
        init_database.session.commit()

        logger.info("Verifying Lookup insertion and relationships")
        assert Lookup.query.count() == 1, "Lookup count mismatch"
        lookup = Lookup.query.first()
        assert lookup.word.word == 'Python', "Word mismatch"
        assert lookup.book_info.title == 'Learn Python Programming', "BookInfo title mismatch"
        assert lookup.usage == 'Python is great!', "Lookup usage mismatch"

        logger.info("Completed test: test_insert_word_and_lookup")

    def test_get_word_lookups_after_timestamp(self, init_database):
        logger.info("Starting test: test_get_word_lookups_after_timestamp")

        # Assuming a fixture or a previous test has populated the database
        test_timestamp = datetime(2023, 4, 27).timestamp()
        results = Lookup.query.filter(Lookup.timestamp > test_timestamp).all()

        logger.info(f"Found {len(results)} results after timestamp {test_timestamp}")
        assert len(results) > 0, "No entries found after the specified timestamp"
        for result in results:
            assert result.timestamp > test_timestamp, "Timestamp mismatch"

        logger.info("Completed test: test_get_word_lookups_after_timestamp")

    def test_set_and_get_latest_timestamp(self, init_database):
        logger.info("Starting test: test_set_and_get_latest_timestamp")

        timestamp = int(datetime(2023, 4, 28).timestamp())
        word = Word(word='Test')
        book_info = BookInfo(title='Test Title', authors='Author Test')
        lookup = Lookup(word=word, book_info=book_info, usage='Test Usage', timestamp=timestamp)
        init_database.session.add(lookup)
        init_database.session.commit()

        latest_timestamp = init_database.session.query(db.func.max(Lookup.timestamp)).scalar()
        assert latest_timestamp == timestamp, "Latest timestamp mismatch"

        logger.info("Completed test: test_set_and_get_latest_timestamp")
