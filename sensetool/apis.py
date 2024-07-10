import json
import random
import requests
import base64
import os
import concurrent.futures
import json
import shutil
from openai import OpenAI
from PIL import Image
import imghdr
import base64
import io
import httpx
import os
import time
import random
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
import dashscope

from http import HTTPStatus
import dashscope
from dashscope import MultiModalConversation
import os
import time
import json



def _encode_image_to_base64(image_path):
    # 打开图像并转换为 RGB 模式
    with Image.open(image_path) as img:
        img = img.convert('RGB')
        
        # 创建一个字节流对象来保存图像数据
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")  # 将图像保存为 JPEG 格式到字节流中
        
        # 读取字节流的内容并编码为 base64
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return img_str
    
def api_request_internl_singleturn(name, question, image, url,
    param =  {
        "max_new_tokens": 1024,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 0.95,
        "repetition_penalty": 1.0,
    }):
    '''
    使用internl模型

    name：模型部署名

    question：给模型的文字输入

    image：给模型图片输入的具体地址

    url：模型部署的地址
    '''
    data = {
    "model" :name,
    "messages": [
        {
            "user": {
                "text": question,
                "images": [
                    _encode_image_to_base64(image),
                ]
            }
        }
    ],
    "param": param
}

    response = requests.post(url, json=data,)
    try:
        response = response.json()
        print(response["answer"])
    except:
        print("wrong answer")
        return False
    return response["answer"]

def internlAPI_singalturn(data, url, optfilepath, num_worker=25):
    '''
    批量数据使用部署的模型(单轮)，输出到文件中,未集成断点继续功能

    data：[{
            "question":xx,
            "image":imagepath,
            "name":模型部署名,
            },...]
    url:部署模型的地址

    optfilepath：生成后文件存放位置
    '''
    def _worker_fn(i):
        # print(i)
        path = i["image"]
        question = i["question"]

        res = api_request_internl_singleturn(i["name"],question, path, url) 
        if not res:
            return
        i["result"] = res
        i["tag"] = url
        with open(optfilepath,"a") as f:
            f.write(json.dumps(i, ensure_ascii=False))
            f.write("\n")
        print(i["image"])

    print(f"数据量：{len(data)}")
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_worker) as executor:
        for i in executor.map(_worker_fn, data):
            pass



def read_gpt_keys(key_file):
    '''
    获取gpt key，把key按行放在文件中读取
    '''
    keys = open(key_file).readlines()
    outputs = []
    for k in keys:
        k = k.strip()
        if len(k):
            outputs.append(k)
    return outputs

def _random_get_proxy(proxy_dict, idx):
    
    data = proxy_dict
    proxys = []
    for key, value in data.items():
        proxys += value
    # print(len(proxys), idx%len(proxys))
    return proxys[idx%len(proxys)]

def api_request_gpt4o_singleturn(api_key: str,
                                infos: dict,
                                prompt,
                                image_size=(1024, 1024),
                                detail='high',
                                proxy_dict=None,
                                api_idx=None):
    '''
    单次使用gpt api

    Args:
        api_key: str key
        infos:传入数据格式：{"image": "",
                            "height": 0,
                            "width": 0,
                            "questions": ,
                            "tag": "",}
        prompt:gpt prompt，prompt中被替换的文字用<<<text>>>表示
        image_size:(int,int) 规定gpt输入图的大小 ** 如不传入图片使用None **
        detail:gpt输入分辨率
        proxy_dict:代理文件读出的dict, ** M集群不用代理，使用None **
        api_idx:代理文件中id，指定使用的代理

    Returns:
            {
            "image": infos["image"],
            "width": w,
            "height": h,
            "result": gpt输出,
        }
    prompt example:
        - Task: 根据对书图片的ocr结果，首先提问总结书中内容，然后对书中提到的信息进行提问并给出答案，问题需要多样化。
        - OutputFormat: 输出严格按照json_format的格式，包含问题和答案。
        - Workflow:
        1. 对文字进行总结，第一个问答对的问题一定是:总结书中的内容。
        2. 随机找内容的一些信息，并对这些信息进行提问，自己生成回答，答案中要包括推理过程。一共生成3个问答对。
        3. 问答对以JSON格式输出，具体格式严格按照json_format中输出。

        - OCR=
            <<<text>>>

        - json_format= 
        {
            "questions": [
                {
                "question": "",
                "answer": ""
                },
                {
                "question": "",
                "answer": ""
                },
                {
                "question": "",
                "answer": ""
                }
            ]
        }
    '''
    if proxy_dict != None:
        proxy_url = _random_get_proxy(proxy_dict, api_idx)
        # proxy_url = 'socks5://10.140.90.11:10200'
        proxies = {
        "http://": f"{proxy_url}",
        "https://": f"{proxy_url}",
        }
    else:
        proxies = None
    http_c = httpx.Client(proxies=proxies)
    # http_c = httpx.Client()
    client = OpenAI(api_key=api_key, http_client=http_c)
    time.sleep(2)

    content = []
    tmp_text = prompt.replace("<<<text>>>", infos["questions"])
    print(tmp_text)
    content.append({"type": "text", "text": tmp_text})
    imagepath = infos["image"]

    if imagepath != None:
        image_type = imghdr.what(imagepath)
        with Image.open(imagepath) as img:
            if img.size[0] > image_size[0] or img.size[1] > image_size[1]:
                img.thumbnail(image_size, Image.LANCZOS)
            w, h = img.size
            byte_stream = io.BytesIO()
            img.save(byte_stream, format=image_type)
            encoded_string = base64.b64encode(byte_stream.getvalue()).decode('utf-8')

        img_src_attr_value = f'data:image/{image_type};base64,{encoded_string}'
        content.append({"type": "image_url", "image_url": {"url": img_src_attr_value, "detail": detail}})
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=4096,
        )
    print(infos["image"])
    try:
        res = response.choices[0].message.content
    except:
        print("output format wrong")
        return False
    save_item = {
        "image": infos["image"],
        "width": w,
        "height": h,
        "result": res,
    }
    print(res)
    return save_item



def api_request_qwen(local_file, question, key, model="qwen-vl-plus"):
    """使用qwen

    Args:
        local_file (_type_): 图片文件地址
        question (_type_): 问题
        key (_type_): api-key
        model(str): 模型名字
    Returns:
        str: 模型返回结果
    """
    
    """Sample of use local file.
       linux&mac file schema: file:///home/images/test.png
       windows file schema: file://D:/images/abc.png
    """

    dashscope.api_key = key 
    local_file_path = f'file://{local_file}'
    messages = [{
        'role': 'system',
        'content': [{
            'text': 'You are a helpful assistant.'
        }]
    }, {
        'role':
        'user',
        'content': [
            {
                'image': local_file_path
            },
            {
                'text': question
            },
        ]
    }]
    response = MultiModalConversation.call(model=model, messages=messages)
    if response.status_code == 200:
        try:
            result_content = response.output.choices[0].message.content[0]['text']
            if not result_content:
                print(response)
            return result_content
        except:
            return ""
    else:
        print(response)
        return ""






    
    


