from copy import deepcopy
import io
import random
import string
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2
from datetime import datetime

def gettime():
    """
    获取时间戳str，YYYMMDD形式
    """
    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y%m%d")
    return formatted_time

def gettxt_list(promptfile):
    '''
    所有可以分行读取的文件均可，返回每行内容的列表，无换行符
    
    （输入prompt文件地址，返回prompt列表）
    '''
    prompts = []
    with open(promptfile, 'r') as f:
        for line in f:
            prompts.append(line.strip())
    return prompts

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

# def get_aoss_file(self, file_path):
#     assert file_path.startswith('s3://')
#     parsed_url = urlparse(file_path)
#     bucket = parsed_url.netloc
#     prefix = parsed_url.path.lstrip("/")

#     try:
#         # Fetch the file from S3
#         # print(f'bucket={bucket}, prefix={prefix}')
#         response = self.s3_client.get_object(Bucket=bucket, Key=prefix)
        
#         # Read the content of the file
#         file_content = response['Body'].read()
#         return file_content

#     except NoCredentialsError:
#         print("Credentials are not available")
#     except Exception as e:
#         print(f"An error occurred: {e}")

def get_image(url, boto3_client = None):
    """获取图片

    Args:
        url (str): 图片地址，本地或ceph均可
        boto3_client (Boto3Client): 传入ceph client，默认为None

    Returns:
        Image.image: 图像
    """    
        
    if isinstance(url, Path):
        url = str(url)
    
    image_bytes = None
    if not url.startswith('s3://'):
        with open(url, 'rb') as fp:
            image_bytes = fp.read()
    else:
        # from aoss_client.client import Client
        image_bytes = boto3_client.get(url)
    assert image_bytes is not None, f'image is None, image={url}'
    image = bytes_to_image(image_bytes)
    return image

def get_file(url, boto3_client=None):
    """获取文件

    Args:
        url (str): 文件地址，本地或ceph均可
        boto3_client (Boto3Client): 传入ceph client，默认为None

    Returns:
        file_bytes: 文件
    """    

    if isinstance(url, Path):
        url = str(url)
    
    file_bytes = None
    if not url.startswith('s3://'):
        with open(url, 'rb') as fp:
            file_bytes = fp.read()
    else:
        file_bytes = boto3_client.get(url)
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
    """生成随机ID

    Args:
        k (int, optional): 长度. Defaults to 8.

    Returns:
        str: str ID
    """
    return ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=k))

def print_divider(text, width=50, divider='='):
    """
    打印一整行分割线，包含居中对齐的文本，每次打印的文本都具有相同的长度。

    参数：
    text: 要打印的文本
    width: 整行的宽度，包含分割符号和文本
    divider: 用于分割的符号
    """
    text_length = len(text)
    if text_length > width - 2:
        raise ValueError("Text is too long for the specified width")
    
    # 计算左右分隔符的长度
    total_divider_length = width - text_length - 2
    left_divider_length = total_divider_length // 2
    right_divider_length = total_divider_length - left_divider_length
    
    # 构建分割行
    divider_line = f"{divider * left_divider_length} {text} {divider * right_divider_length}"
    
    print(divider_line)