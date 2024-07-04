import json
from pathlib import Path
import random

import traceback
import time

import requests
import io
import sys
from copy import deepcopy
import asyncio
import logging
import zipfile
import pickle
import numpy as np

def set_logging(log_file, name=None):
    """
    Set up logging configuration.

    Args:
        log_file (str): The path to the log file.
        name (str, optional): The name of the logger. Defaults to None.
    """
    Path(log_file).parent.mkdir(exist_ok=True, parents=True)
    logging.basicConfig(filename=str(log_file), 
                    level=logging.INFO,
                    format=f'%(asctime)s - rank={name} - %(name)s - %(levelname)s - %(message)s')

def get_logger(log_file, name=None):
    name = str(name)
    formatter = logging.Formatter(f'%(asctime)s - rank={name} - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

def read_lines(file):
    outputs = []
    for line in open(file).readlines():
        line = line.rstrip()
        if line:
            outputs.append(line)
    return outputs    

def read_jsonl(file, client=None):
    """读取jsonl文件

    Args:
        file (str): 文件path
        client (_type_, optional): 如果在ceph上传入client以读取. Defaults to None.

    Returns:
        list: 每条为list中一项
    """    
    if client is None or not file.startswith('s3://'):
        assert Path(file).is_file(), file
        dataset = open(file, buffering=int(32e6)).readlines()
    else:
        data_str = client.get(file).decode()
        data_io = io.StringIO(data_str)
        dataset = data_io.readlines()
    outputs = []
    for i, line in enumerate(dataset):
        line = line.rstrip()
        if line:
            try:
                outputs.append(json.loads(line))
            except Exception as e:
                print(f'i={i}, line={line}')
                # raise e
    return outputs


def parse_jsonl_str(data):
    outputs = []
    for line in data.split('\n'):
        if not line:
            continue
        else:
            outputs.append(json.loads(line))
    return outputs

def write_jsonl(file, data):
    """写入jsonl文件，list每个对应每行

    Args:
        file (str): 写入文件的地址
        data (list): 写入内容
    """    
    fp = open(file, 'w', encoding='utf-8', buffering=int(32e6))
    for d in data:
        fp.write(json.dumps(d, ensure_ascii=False) + '\n')

class JsonlWriter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.fp = open(self.file_path, 'a', encoding='utf-8')

    def write(self, data):
        self.fp.write(json.dumps(data, ensure_ascii=False) + '\n')
        self.fp.flush()








def retry_decorator(max_retries=1, delay=0, name=None, logger=None):
    if logger is None:
        class FakeLogger:
            def error(*args, **kwargs):
                print(*args, **kwargs)
        logger = FakeLogger()
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.error(f"Retry.{name} Attempt {attempts + 1} failed. Exception: {e}, TraceBack: {traceback.format_exc()}")
                    attempts += 1
                    time.sleep(delay)
            raise Exception(f"Retry.{name} Max retries ({max_retries}) reached. Function {func.__name__} failed.")
        return wrapper
    return decorator

def insert_image_token(text):
    insert_at_front = random.choice([True, False])
    if insert_at_front:
        result = '<image>\n' + text
    else:
        result = text + '\n<image>'
    return result




def random_get_proxy(file, idx):
    fr = open(file, 'r', encoding='utf-8')
    data = json.load(fr)
    proxys = []
    for key, value in data.items():
        proxys += value
    fr.close()
    return proxys[idx % len(proxys)]

def requests_get(*args, **kwargs):
    if 'timeout' in kwargs:
        timeout = kwargs.pop('timeout')
    else:
        timeout = None
    if timeout is None or timeout <= 0:
        requests.get(*args, **kwargs)
    else:
        async def main():
            try:
                async with asyncio.timeout(5):
                    result = await requests.get(*args, **kwargs)
                    print(result)
            except asyncio.TimeoutError:
                print(f'Timeout waiting')
        return asyncio.run(main())

def requests_get(*args, **kwargs):
    timeout = kwargs.pop('timeout', None)

    def trace_function(frame, event, arg):
        if time.time() - start > timeout:
            raise Exception('requests_get Timed out!')

        return trace_function

    start = time.time()
    sys.settrace(trace_function)

    try:
        return requests.get(*args, **kwargs)
    except:
        raise
    finally:
        sys.settrace(None)


def compress_string_to_bytes(input_string):
    bytes_buffer = io.BytesIO()
    
    with zipfile.ZipFile(bytes_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('content.txt', input_string)
        
    return bytes_buffer.getvalue()

def decompress_bytes_to_string(input_bytes):
    bytes_buffer = io.BytesIO(input_bytes)
    
    with zipfile.ZipFile(bytes_buffer, 'r') as zip_file:
        decompressed_string = zip_file.read('content.txt').decode('utf-8')
    
    return decompressed_string


def compress_data(data):
    """
    Compresses the given data using the BZIP2 algorithm and returns the compressed data as bytes.

    Args:
        data: The data to be compressed.

    Returns:
        bytes: The compressed data.

    Example:
        >>> data = [1, 2, 3, 4, 5]
        >>> compressed_data = compress_data(data)
    """
    data_bytes = pickle.dumps(data)
    
    fp = io.BytesIO()
    with zipfile.ZipFile(fp, 'w', zipfile.ZIP_BZIP2) as zip_file:
        zip_file.writestr('content.txt', data_bytes)
    return fp.getvalue()

def decompress_data(input_bytes):
    """
    Decompresses the given input bytes using the ZIP compression algorithm.

    Args:
        input_bytes (bytes): The compressed input bytes.

    Returns:
        object: The deserialized object obtained from decompressing and unpickling the input bytes.
    """
    bytes_buffer = io.BytesIO(input_bytes)
    with zipfile.ZipFile(bytes_buffer, 'r') as zip_file:
        unzip_bytes = zip_file.read('content.txt')
    bytes_buffer.close()
    return pickle.loads(unzip_bytes)

def find_common_root(paths):
    """
    Finds the common root directory among a list of paths.

    Args:
        paths (list): A list of paths.

    Returns:
        str: The common root directory.

    Example:
        >>> paths = ['/home/user/documents/file1.txt', '/home/user/documents/file2.txt']
        >>> find_common_root(paths)
        '/home/user/documents'
    """
    if not paths:
        return ""

    split_paths = [path.split("/") for path in paths]
    common_root = split_paths[0]
    for path in split_paths[1:]:
        common_root = [common_root[i] for i in range(min(len(common_root), len(path))) if common_root[i] == path[i]]
        if not common_root:
            return ""
    return "/".join(common_root)

def replace_punctuation(text):
    # 定义英文标点和对应的中文标点
    punctuation_map = {
        '.': '。',
        ',': '，',
        '?': '？',
        '!': '！',
        ':': '：',
        ';': '；',
        '"': '“',
        '\'': '‘',
        '(': '（',
        ')': '）',
        '[': '【',
        ']': '】',
        '{': '｛',
        '}': '｝',
        '<': '《',
        '>': '》',
        '/': '／',
        '\\': '＼'
    }
    
    # 替换文本中的标点
    for en_punct, zh_punct in punctuation_map.items():
        text = text.replace(en_punct, zh_punct)
    
    return text


