## MQTT client that receives BCP log messages and stores them via LogMessageHandler.

import logging
import queue
import threading

import paho.mqtt.client as paho
from sqlalchemy import create_engine

from logmsgHandler import LogMessageHandler, processor_thread


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    if reason_code_list[0].is_failure:
        logger.error("Broker rejected subscription: %s", reason_code_list[0])
    else:
        logger.info("Broker granted QoS %s", reason_code_list[0].value)


def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
    if len(reason_code_list) == 0 or not reason_code_list[0].is_failure:
        logger.info("Unsubscribe successful")
    else:
        logger.error("Broker replied with failure: %s", reason_code_list[0])
    client.disconnect()


def on_message(client, userdata, message):
    """Enqueue raw payloads; processing happens in the worker thread."""
    topic = message.topic
    payload = message.payload.decode()

    if topic.split("/")[0] == "control":
        logger.info("Control message on %s: %s", topic, payload)
        if "stop" in payload:
            logger.info("Stopping")
            client.disconnect()
        return

    # Enqueue a (topic, payload) tuple so the handler can record the topic
    # and store bad messages with full context.
    userdata.put((topic, payload))
    logger.debug("Enqueued message from %s", topic)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logger.error("Failed to connect: %s", reason_code)
    else:
        logger.info("Subscribing to runs/# and control/#")
        client.subscribe("runs/#")
        client.subscribe("control/#")


def main():
    import argparse

    parser = argparse.ArgumentParser("MQTT <-> SQLite Client")
    parser.add_argument("--db", type=str, default="log.db", help="SQLite database file")
    parser.add_argument(
        "--host", type=str, default="localhost", help="MQTT broker to connect to"
    )
    args = parser.parse_args()

    conn_str = f"sqlite:////{args.db}"
    logger.info("Connecting to database: %s", conn_str)
    db_engine = create_engine(conn_str, echo=False, connect_args={"autocommit": True})

    msg_queue = queue.Queue()
    handler = LogMessageHandler(db_engine)
    stop_event = threading.Event()

    worker = threading.Thread(
        target=processor_thread,
        args=(msg_queue, handler, stop_event),
        daemon=True,
    )
    worker.start()

    client = paho.Client(paho.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_unsubscribe = on_unsubscribe
    client.user_data_set(msg_queue)

    try:
        client.connect(args.host)
    except Exception as exc:
        logger.exception("Failed to connect to MQTT broker")
        stop_event.set()
        worker.join(timeout=2)
        raise

    logger.info("Ready")
    try:
        client.loop_forever()
    finally:
        logger.info("Shutting down worker")
        stop_event.set()
        msg_queue.join()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
