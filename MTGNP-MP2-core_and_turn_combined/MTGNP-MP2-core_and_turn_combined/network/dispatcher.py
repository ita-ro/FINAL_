from shared.errors import ProtocolError

class Dispatcher:
    """
    Routes incoming PDUs to the correct handler.
    """

    def __init__(self, network_manager = None):
        self.handlers = {}
        self.network_manager = network_manager

    def register_handler(self, message_type, handler):
        """
        Registers a handler function for a PDU type.

        Parameters
        ----------
        message_type : str
            PDU type identifier.

        handler : function
            Function that processes the PDU.
        """

        if not isinstance(message_type, str):
            raise ProtocolError("Message type must be a string.")

        if not callable(handler):
            raise ProtocolError("Handler must be callable.")
        
        self.handlers[message_type] = handler

    def dispatch(self, pdu, client):
        """
        Sends a received PDU to its corresponding handler.

        Paramters
        ---------
        pdu : dict
            Received protocol message.

        client : socket.socket
            Client socket that sent the message.
        """

        if not isinstance(pdu, dict):
            print("Invalid PDU: expected dictionary.")
            return

        message_type = pdu.get("type")

        if message_type is None:
            print("PDU missing type.")
            return

        handler = self.handlers.get(message_type)

        if handler is None:
            self.send_error(
                client,
                "UNKNOWN_TYPE",
                f"Unknown PDU type: {message_type}",
                {
                    "type": message_type,
                    "seq_num": pdu.get("seq_num")
                }
            )
            return

        try:
            handler(pdu, client)
        except Exception as ex:
            print(f"Handler error: {ex}")

    def send_error(self, client, code, message, rejected_action = None):
        """
        Sends an ERROR PDU to a client.
        """

        error_pdu = {
            "type": "ERROR",
            "seq_num": self.network_manager.next_server_seq_num(),
            "code": code,
            "message": message
        }

        if rejected_action is not None:
            error_pdu["rejected_action"] = rejected_action

        self.network_manager.send_message(client, error_pdu)