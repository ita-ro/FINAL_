import socket

from network.protocol import send_message, receive_message

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 4444))

message = {
    "type": "PLAYER_READY",
    "seq_num": 1,
    "player_id": "Player2",
    "deck_list": ["white_knight_002"]
}

print("Sending PLAYER_READY...")
send_message(sock, message)

response = receive_message(sock)
print("Received:", response)

send_message(sock, {
    "type": "MULLIGAN_CHOICE",
    "seq_num": 1,
    "keep": True,
    "cards_to_bottom": []
})

input("Press Enter to disconnect...")
sock.close()