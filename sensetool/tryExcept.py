from functools import wraps
import socket


def catch_error_node(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseException as e:
            print(f"Node Error: {socket.gethostname()}", flush=True)
            raise e

    return wrapper

