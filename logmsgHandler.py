"""MQTT log message handler.

"""

import datetime
import json
import logging
import queue
import threading
import traceback
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from logdb import BadMessage, Entry, Test
from message_handlers import get_handler


logger = logging.getLogger(__name__)

# Required keys for the top-level BCP message envelope.
ENVELOPE_KEYS = {
    "location",
    "msg_id",
    "run_number",
    "sm_id",
    "test_id",
    "results",
    "tgid",
    "towers",
    "timestamp",
}

# Required keys for each item in the ``results`` list.
RESULT_KEYS = {"func_name", "timestamp", "result"}


class LogMessageHandler:
    """Process incoming BCP log message payloads and store them in the DB."""

    def __init__(self, db_engine):
        self.db_engine = db_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_payload(self, payload: str, topic: Optional[str] = None) -> bool:
        """Process a single raw MQTT payload.

        Returns ``True`` if the payload was successfully processed and
        ``False`` if it was stored as a bad message.
        """
        try:
            message = self._parse_payload(payload)
            self._validate_envelope(message)
            self._process_message(message)
            return True
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            logger.exception("Failed to process payload: %s", reason)
            self._store_bad_message(payload, reason, topic=topic)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_payload(self, payload: str) -> Dict[str, Any]:
        """Parse the raw payload string into a dict."""
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

    def _validate_envelope(self, message: Dict[str, Any]) -> None:
        """Validate the top-level message envelope."""
        if not isinstance(message, dict):
            raise ValueError("Message is not a JSON object")

        missing = ENVELOPE_KEYS - set(message.keys())
        if missing:
            raise ValueError(f"Missing envelope keys: {sorted(missing)}")

        if not isinstance(message["results"], list):
            raise ValueError("'results' must be a list")

    def _validate_result(self, result: Any, index: int) -> None:
        """Validate a single result item."""
        if not isinstance(result, dict):
            raise ValueError(f"Result at index {index} is not an object")

        missing = RESULT_KEYS - set(result.keys())
        if missing:
            raise ValueError(
                f"Result at index {index} missing keys: {sorted(missing)}"
            )

    def _process_message(self, message: Dict[str, Any]) -> None:
        """Process each result in a validated message."""
        run_number = message["run_number"]
        test_id_name = message["test_id"]

        with Session(self.db_engine) as session:
            test = self._get_test(session, test_id_name)
            if test is None:
                raise ValueError(f"Unknown test_id: {test_id_name}")

            for index, result in enumerate(message["results"]):
                self._validate_result(result, index)
                handler = get_handler(result.get("func_name", "unknown"))
                processed = handler(result)
                self._store_entry(
                    session,
                    run_number=run_number,
                    test_id=test.id,
                    func_name=processed["func_name"],
                    result=processed["result"],
                    timestamp=processed["timestamp"],
                )

            session.commit()

    def _get_test(self, session: Session, test_id_name: str) -> Optional[Test]:
        """Look up a Test row by name."""
        return session.execute(
            select(Test).where(Test.name == test_id_name)
        ).scalar_one_or_none()

    def _store_entry(
        self,
        session: Session,
        run_number: int,
        test_id: int,
        func_name: str,
        result: Any,
        timestamp: Any,
    ) -> None:
        """Insert a processed result into ecal_logger_entries."""
        entry = Entry()
        entry.run_number = run_number
        entry.test_id = test_id
        entry.func_name = func_name
        entry.result = json.dumps(result)
        entry.test_timestamp = timestamp
        session.add(entry)

    def _store_bad_message(
        self,
        payload: str,
        reason: str,
        topic: Optional[str] = None,
    ) -> None:
        """Persist a malformed/unprocessable payload for later inspection."""
        try:
            with Session(self.db_engine) as session:
                bad = BadMessage()
                bad.received_at = datetime.datetime.now(datetime.timezone.utc)
                bad.topic = topic
                bad.payload = payload
                bad.reason = reason
                bad.exception = traceback.format_exc()
                session.add(bad)
                session.commit()
        except Exception as exc:
            # Last-resort logging: we cannot even store the bad message.
            logger.error("Failed to store bad message: %s", exc)


# ----------------------------------------------------------------------
# Worker thread helpers
# ----------------------------------------------------------------------
def processor_thread(msg_queue: queue.Queue, handler: LogMessageHandler, stop_event: threading.Event) -> None:
    """Consume raw payloads from ``msg_queue`` and process them.

    The caller should set ``stop_event`` to request a clean shutdown.
    """
    while not stop_event.is_set():
        try:
            item = msg_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        # Accept either a raw string or a (topic, payload) tuple.
        if isinstance(item, tuple):
            topic, payload = item
        else:
            topic, payload = None, item

        handler.handle_payload(payload, topic=topic)
        msg_queue.task_done()

    logger.info("Finished processor thread")


if __name__ == "__main__":
    # Minimal interactive sanity test.
    logging.basicConfig(level=logging.INFO)

    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///log.db")
    handler = LogMessageHandler(engine)
    q: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    thr = threading.Thread(
        target=processor_thread, args=(q, handler, stop_event), daemon=True
    )
    thr.start()

    for _ in range(5):
        msg = input("msg=")
        q.put(msg)

    q.join()
    stop_event.set()
    thr.join()
