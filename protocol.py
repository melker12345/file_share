import json


LIST_REQUEST = "LIST_REQUEST"
LIST_RESPONSE = "LIST_RESPONSE"
FILE_REQUEST = "FILE_REQUEST"
FILE_RESPONSE = "FILE_RESPONSE"
SEND = "SEND"
QUIT = "QUIT"
HEARTBEAT = "HEARTBEAT"

def pack(msg_type, data):
    msg_dict = {"type": msg_type, "data": data}
    json_msg = json.dumps(msg_dict)
    json_encoded = json_msg.encode()
    return json_encoded

def unpack(data):
    message = json.loads(data.decode())
    return message["type"], message["data"]
