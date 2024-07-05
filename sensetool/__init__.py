'''
工具包
1. checkfiles(filepath) 传入数据汇总文件，检查数据正确性
2. startView() 带图数据浏览，创建ipynb文件
3. jsonl:
    read_jsonl(filepath) 
    write_jsonl(file, data)
4. apis: 
    api_request_internl_singleturn(name, question, image, url) 单轮internl
    internlAPI_singalturn(data, url, optfilepath, num_worker=25) 批量过internl
    read_gpt_keys(key_file) 读取gpt key
    api_request_gpt4o_singleturn(api_keys: list,
                                infos: dict,
                                prompt,
                                image_size=(1024, 1024),
                                detail='high',
                                proxy_file='socks_240318_ids_5_r280.json',
                                api_idx=40101) 单次过gpt
    api_request_qwen(local_file, question, key) 单次过qwen
5. basic
    get_image(url)  获取图片
    getprompt(promptfile) 获取prompt
    print_divider(text) 打印分隔
'''

from .checkdata import (
    checkfiles
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
    getprompt,
    print_divider
)
def start():
    print("import successful")