from copy import deepcopy
import io
import random
import string
import numpy as np
from .boto3client import Boto3Client
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2


def bytes_to_image(data):
    """
    Converts a byte array to an image object.

    Args:
        data (bytes): The byte array representing the image.

    Returns:
        PIL.Image.Image: The image object.

    Example:
        >>> data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90\x8d\x8f\xae\x00\x00\x00\x0cIDAT\x08\xd7c```\x00\x00\x00\x02\x00\x01\x8d\x0b\xfc\x00\x00\x00\x00IEND\xaeB`\x82'
        >>> image = bytes_to_image(data)
    """
    image_io = io.BytesIO()
    image_io.write(data)
    image_io.seek(0)
    image = Image.open(image_io)
    return image


_boto3_client = None
def get_image(url):
    global _boto3_client
    if _boto3_client is None:
        _boto3_client = Boto3Client()
        
    if isinstance(url, Path):
        url = str(url)
    
    image_bytes = None
    if not url.startswith('s3://'):
        with open(url, 'rb') as fp:
            image_bytes = fp.read()
    else:
        image_bytes = _boto3_client.get(url)
    assert image_bytes is not None, f'image is None, image={url}'
    image = bytes_to_image(image_bytes)
    return image

def get_file(url):
    global _boto3_client
    if _boto3_client is None:
        _boto3_client = Boto3Client()
        
    if isinstance(url, Path):
        url = str(url)
    
    file_bytes = None
    if not url.startswith('s3://'):
        with open(url, 'rb') as fp:
            file_bytes = fp.read()
    else:
        file_bytes = _boto3_client.get(url)
    assert file_bytes is not None, f'file_bytes is None, url={url}'
    return file_bytes

def draw_rectangles_with_text(img, data, width=1, font_size=12):
    """
    Draw rectangles with text using PIL.
    
    :param data: A list of lists, where each sublist contains four numbers representing
                 xmin, ymin, xmax, ymax of a rectangle, followed by a string of text.
    """
    # Create a blank image
    img = deepcopy(img)
    draw = ImageDraw.Draw(img)

    # Load a font
    font_path = '/mnt/afs1/luojiapeng/.fonts/msyh.ttc'
    font = ImageFont.truetype(font_path, font_size)

    for item in data:
        if len(item) == 2:
            (xmin, ymin, xmax, ymax), text = item
        elif len(item) == 4:
            xmin, ymin, xmax, ymax = item
            text = ''
        elif len(item) == 5:
            xmin, ymin, xmax, ymax, text = item
        else:
            raise ValueError(f'wrong data length={len(item)}: {item}')
        # Draw a rectangle
        draw.rectangle([(xmin, ymin), (xmax, ymax)], outline="red", width=width)
        loc_y = max(0, ymin - font_size - 1)
        draw.text((xmin + 1, loc_y), text, fill="red", font=font)
    return img

def get_bbox(char_img: np.ndarray) -> tuple:
    """
    Calculates the bounding box coordinates for a character image.

    Args:
        char_img (np.ndarray): The character image as a NumPy array.

    Returns:
        tuple: A tuple containing the x, y, width, and height of the bounding box.
    """
    if char_img.dtype == np.dtype(bool):
        char_img = char_img.astype(np.uint8) * 255
    img = cv2.cvtColor(char_img, cv2.COLOR_BGR2GRAY) if len(char_img.shape) == 3 else char_img
    _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY)
    img = 255 - img
    edges = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[0]
    if len(edges) > 0:
        edges = np.concatenate(edges, axis=0)
        x, y, w, h = cv2.boundingRect(edges)
        return (x, y, w, h)
    else:
        return 0, 0, 0, 0

def split_list_into_parts(lst, n):
    """
    Split a list into n parts.

    This function takes a list and splits it into n approximately equal parts. If the length of the list is not evenly divisible by n, 
    the remaining elements will be distributed among the parts in a round-robin fashion.

    Parameters:
    lst (list): The list to be split.
    n (int): The number of parts to split the list into.

    Returns:
    list: A list of lists, where each sublist is a part of the original list.

    Example:
    >>> split_list_into_parts([1, 2, 3, 4, 5, 6, 7, 8, 9], 3)
    [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    >>> split_list_into_parts([1, 2, 3, 4, 5, 6, 7, 8, 9], 4)
    [[1, 2], [3, 4], [5, 6], [7, 8, 9]]
    """
    part_length = len(lst) // n
    remainder = len(lst) % n

    result = []
    start = 0

    for i in range(n):
        end = start + part_length + (1 if i < remainder else 0)
        result.append(lst[start:end])
        start = end

    return result

def randomID(k=8):
    return ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=k))