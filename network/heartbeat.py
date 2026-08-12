import threading
import time

from network.protocol import send_message


def handle_ping(pdu, client_socket):
    """
    Responds to a client PING with a PONG.

    The PONG echoes the PING's seq_num and timestamp.
    """

    pong = {
        "type": "PONG",
        "seq_num": pdu["seq_num"],
        "timestamp": pdu["timestamp"],
    }

    send_message(client_socket, pong)


class HeartbeatManager:
    """
    Manages client-side PING messages and PONG timeouts.
    """

    def __init__(self, client, interval=30, timeout=10):
        self.client = client
        self.interval = interval
        self.timeout = timeout

        self.running = False
        self.thread = None
        self.last_ping_time = None
        self.last_ping_seq = None

    def start(self):
        """
        Starts the heartbeat thread.
        """

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

    def stop(self):
        """
        Stops the heartbeat thread.
        """

        self.running = False

    def _run(self):
        """
        Periodically sends PING messages and checks for timeout.
        """

        last_ping = time.monotonic()

        while self.running:
            time.sleep(1)

            now = time.monotonic()

            if now - last_ping >= self.interval:
                self.send_ping()
                last_ping = now

            if self.check_timeout():
                print("Heartbeat timeout. Server did not respond to PING.")
                self.client.running = False
                self.running = False

    def send_ping(self):
        """
        Sends a PING to the server.
        """

        timestamp = int(time.time() * 1000)
        seq_num = self.client.next_seq_num()

        self.last_ping_time = time.monotonic()
        self.last_ping_seq = seq_num

        ping = {
            "type": "PING",
            "seq_num": seq_num,
            "timestamp": timestamp,
        }

        try:
            self.client.send_message(ping)
        except OSError:
            self.client.running = False

    def handle_pong(self, pdu):
        """
        Handles a PONG received from the server.
        """

        if pdu.get("seq_num") != self.last_ping_seq:
            return

        self.last_ping_time = None
        self.last_ping_seq = None

    def check_timeout(self):
        """
        Returns True if the current PING has timed out.
        """

        if self.last_ping_time is None:
            return False

        return (
            time.monotonic() - self.last_ping_time
            > self.timeout
        )