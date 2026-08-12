import socket, pytest

from network.protocol import send_message, receive_message
from shared.errors import ProtocolError

def create_socket_pair():
    """
    Creates connected sockets for testing.
    """
    server_socket, client_socket = socket.socketpair()
    return server_socket, client_socket

def test_send_receive_message():
    sender, receiver = create_socket_pair()

    message = {
        "type": "PLAYER_READY",
        "seq_num": 1,
        "player_id": "Alice",
        "deck_list": [
            "mountain_001",
            "lightning_bolt_001"
        ]
    }

    send_message(sender, message)
    received = receive_message(receiver)
    assert received == message

    sender.close()
    receiver.close()

def test_missing_type_field():
    sender, receiver = create_socket_pair()

    message = {
        "seq_num": 1,
        "player_id": "Alice"
    }

    with pytest.raises(ProtocolError):
        send_message(sender, message)

    sender.close()
    receiver.close()

def test_missing_sequence_number():
    sender, receiver = create_socket_pair()

    message = {
        "type": "PLAYER_READY",
        "player_id": "Alice"
    }

    with pytest.raises(ProtocolError):
        send_message(sender, message)

    sender.close()
    receiver.close()

def test_message_must_be_dictionary():
    sender, receiver = create_socket_pair()

    message = [
        "PLAYER_READY",
        1
    ]

    with pytest.raises(ProtocolError):
        send_message(sender, message)

    sender.close()
    receiver.close()

def test_multiple_pdu_types():
    sender, receiver = create_socket_pair()

    messages = [
        {
            "type": "PLAYER_READYER",
            "seq_num": 1,
            "player_id": "Alice"
        },
        {
            "type": "GAME_START",
            "seq_num": 2,
            "starting_player": "Alice"
        },
        {
            "type": "PLAY_CARD",
            "seq_num": 3,
            "card_id": "lightning_bolt_001"
        }
    ]

    for message in messages:
        send_message(sender, message)
        received = receive_message(receiver)
        assert received == message

    sender.close()
    receiver.close()

def test_large_message():
    sender, receiver = create_socket_pair()

    message = {
        "type": "PLAYER_READY",
        "seq_num": 1,
        "player_id": "Alice",
        "deck_list": [
            f"card_{i}"
            for i in range(100)
        ]
    }

    send_message(sender, message)
    received = receive_message(receiver)
    assert received == message

    sender.close()
    receiver.close()