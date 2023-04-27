import os
import sqlite3
import time
import shutil
import datetime
from sqlite3 import Connection


MACOS_TARGET_VOCAB_MOUNT_FILE_LOC = "/Volumes/Kindle/system/vocabulary/vocab.db"
_latest_timestamp: int = -1


def establish_a_connection(db_file_path: str) -> Connection:
    return sqlite3.connect(db_file_path)


def copy_vocab_db_to_backup_and_tmp_upon_proper_access(count: int):
    project_root = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(project_root, "backup")
    tmp_dir = os.path.join(project_root, "tmp")
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)
    while not os.path.exists(MACOS_TARGET_VOCAB_MOUNT_FILE_LOC):
        time.sleep(2)
        count += 1
    copy_vocab_db(count, MACOS_TARGET_VOCAB_MOUNT_FILE_LOC, backup_dir, tmp_dir)


def copy_vocab_db(count: int, vocab_file_path: str, backup_dir: str, tmp_dir: str):
    start_time = time.monotonic()
    shutil.copy(vocab_file_path, backup_dir)
    shutil.copy(vocab_file_path, tmp_dir)
    end_time = time.monotonic()
    elapsed_time = end_time - start_time
    file_size = os.path.getsize(vocab_file_path) / 1024  # Get file size in KB
    print()
    print(f"vocab.db copied to backup and tmp folders for the {count}{ordinal_suffix(count)} time "
          f"(elapsed time: {elapsed_time:.2f}s, file size: {file_size:.2f} KB)")


def try_to_get_tmp_db_path() -> str:
    project_root = os.path.dirname(os.path.abspath(__file__))
    tmp_dir = os.path.join(project_root, "tmp")
    if os.path.exists(tmp_dir):
        return tmp_dir
    raise FileNotFoundError("the fuckk, local db doesnt (seem to0)exist asshole, 多分 you fucked up the mount function")


def get_table_info(db_connection_injection: Connection) -> dict:
    table_info = {}
    with db_connection_injection:
        cursor = db_connection_injection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[0]
            table_columns = {}
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for column in columns:
                column_name = column[1]
                data_type = column[2]
                table_columns[column_name] = data_type

            table_info[table_name] = table_columns

    return table_info


def get_all_word_look_ups_after_timestamp(connection: Connection, timestamp: int) -> list[dict]:
    with connection as connection:
        query = f"""
            SELECT LOOKUPS.id, WORDS.word, LOOKUPS.usage, LOOKUPS.timestamp, BOOK_INFO.title, BOOK_INFO.authors
            FROM LOOKUPS 
            JOIN WORDS ON LOOKUPS.word_key = WORDS.id 
            JOIN BOOK_INFO ON LOOKUPS.book_key = BOOK_INFO.id 
            WHERE LOOKUPS.timestamp >= {timestamp}
        """
        return execute_query(connection, query)


def get_latest_lookup_timestamp(connection: Connection):
    with connection:
        query = "SELECT MAX(timestamp) AS latest_lookup_timestamp FROM LOOKUPS"
        return execute_query(connection, query)


def execute_query(connection: Connection, query: str) -> list[dict]:
    with connection:
        cursor = connection.cursor()
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results


# AUXILIARIES
def ordinal_suffix(count: int) -> str:
    if 11 <= count <= 13:
        return "th"
    elif count % 10 == 1:
        return "st"
    elif count % 10 == 2:
        return "nd"
    elif count % 10 == 3:
        return "rd"
    else:
        return "th"


def get_timestamp_ms(year, month, day):
    dt = datetime.datetime(year=year, month=month, day=day)
    return int(dt.timestamp() * 1000)