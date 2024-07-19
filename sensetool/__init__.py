'''
工具包
1. 检查数据
    - c = checker(client)
    - c.checkfiles(filepath) 传入数据汇总文件，检查数据正确性
2. startView() 带图数据浏览，创建ipynb文件
3. ceph
    - Boto3Client(endpoint_url, access_key, secret_key) ceph的client，获取ceph数据前需启动client
    - AossClient(endpoint_url, access_key, secret_key)
4. jsonl:
    - read_jsonl(file, client=None) 
    - write_jsonl(file, data)
5. apis: 
    - 单轮internl: api_request_internl_singleturn(name, question, image, url) 
    - 批量过internl: internlAPI_singalturn(data, url, optfilepath, num_worker=25) 
    - 读取gpt key: read_gpt_keys(key_file) 
    - 单次过gpt: api_request_gpt4o_singleturn(api_keys: list,
                                infos: dict,
                                prompt,
                                image_size=(1024, 1024),
                                detail='high',
                                proxy_dict=None,
                                api_idx=None) 
    - 单次过qwen: api_request_qwen(local_file, question, key, model) 

6. basic
    - 获取图片: get_image(url, boto3_client = None) 
    - 获取文件: get_file(url, boto3_client = None) 
    - 获取文件内容无换行符: gettxt_list(promptfile) 
    - 打印分隔: print_divider(text) 
7. time
    - time.timer_decorator(func) 函数时间计算装饰器 
'''

from .checkdata import (
    checker
)

from .jsonl import (
    read_jsonl,
    write_jsonl,
)

from .view import (
    startView
)

from .apis import(
    api_request_internl_singleturn,
    internlAPI_singalturn,
    read_gpt_keys,
    api_request_gpt4o_singleturn,
    api_request_qwen,

)

from .basic import (
    get_image,
    get_file,
    gettxt_list,
    print_divider
)
from .boto3client import Boto3Client
from .aossclient import AossClient

def start():
    print("import successful")