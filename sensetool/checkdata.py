
import json
from pathlib import Path
import random
import traceback
import time, os
import pandas as pd
import concurrent.futures
import threading
from easydict import EasyDict as edict
from .basic import get_image
from .jsonl import read_jsonl

class checker():
    """数据检查
    """
    def __init__(self, client=None) -> None:
        """初始化

        Args:
            client (aossclient): ceph客户端
        """
        self._AossClient = client

    def _check_format(self, dataset):
        for index, data in enumerate(dataset):
            # if 'image' in data and data['image'] is not None:
            #     if 'width' not in data or 'height' not in data:
            #         return f"index={index}, no width or height"
            #     if not (isinstance(data['width'], int) and data['width'] > 0):
            #         return f'index={index}, data["width"] = ({type(data["width"])}) {data["width"]}'
            #     if not (isinstance(data['height'], int) and data['height'] > 0):
            #         return f'index={index}, data["height"] = ({type(data["height"])}) {data["height"]}'
            if len(data['conversations']) < 2 or len(data['conversations']) % 2 != 0:
                return f"index={index}, Not correct number: {index}"
            for i, message in enumerate(data['conversations']):
                if i == 0:
                    if not message['value'].startswith('<image>\n'):
                        return f"index={index}, No <image> tag: {index}, {message['value']}"
                if i > 0:
                    if '<image>' in message['value']:
                        return f"index={index}, extra <image> tag: {index}"
                if not isinstance(message['value'], str):
                    return f"index={index}, Not correct format: it should be a string: {index}"
                if not (len(message['value']) > 0):
                    return f"index={index}, No Message: {data}: {index}"
                if i % 2 == 0:
                    if not (message['from'] == 'human'):
                        return f"index={index}, Not from human: {data}: {index}"
                else:
                    if not (message['from'] == 'gpt'):
                        return f"index={index}, Not from gpt: {data}: {index}"

    def _check_image_correct(self, dataset, image_root):
        cnt_fail = 0
        cnt_success = 0
        ret = True
        for data in dataset:
            if 'image' not in data:
                continue
            image_name = data['image']
            image_file = os.path.join(image_root, image_name)
            try:
                image = get_image(image_file, self._AossClient)
                cnt_success += 1
            except:
                cnt_fail += 1
                print(f"image={image_name}, get fail, image_url={image_file}")
                ret = ret and False
            # width, height = image.size
            # if width != data['width'] or height != data['height']:
            #     print(f"image={image_name}, wrong image size, image_url={image_file}")
            #     ret = ret and False
        # print(f'image path check, cnt_success={cnt_success}, cnt_fail={cnt_fail}')
        return ret


    def worker_fn(self, meta):
        try:
            json_file = meta['text_file']
            image_root = meta['image_path']
            # print(f'>>> input={json_file}')
            dataset = read_jsonl(json_file, self._AossClient)
            # print(f'number={len(dataset)}')
            msg = self._check_format(dataset)
            # msg = None
            if msg is None:
                # return "sesecore cannot access mst images, other format correct"
                mini_dataset = random.choices(dataset, k=100)
                if self._check_image_correct(mini_dataset, image_root):
                    msg = 'check image success.'
                    return msg
                else:
                    msg = 'Error: image check fail'
                    return msg
            else:
                msg = f'Error: format is incorrect. msg={msg}'
                return msg
        except:
            print(traceback.format_exc())
            return "Error: unexpected error"

    def _checkdata(self, meta_dataset):
        with concurrent.futures.ProcessPoolExecutor(max_workers=16) as executor:
            for meta, msg in zip(meta_dataset, executor.map(self.worker_fn, meta_dataset)):
                print('\n>>>>>>')
                print(meta)
                print(msg)


    # 数据脚本验证
    def checkfiles(self, filepath):
        '''
        传入数据汇总文件，检查所有数据是否正确，目前只支持图像数据
        
        汇总文件格式：{
                    'annotation':text_file,
                    'root':image_path
                    },...
        也可传入dict：{
                    'annotation':text_file,
                    'root':image_path
                    }
        也可传入list：[{
                    'annotation':text_file,
                    'root':image_path
                    },...]
        也可传入metadata_dict:{
        "data_name":{
                    'annotation':text_file,
                    'root':image_path
                    },...
        }            
        '''
        input_list = []
        if isinstance(filepath, str) and os.path.exists(filepath):
            meta_dataset = json.load(open(filepath))
            for k, meta in meta_dataset.items():
                input_list.append({
                    'text_file': meta['annotation'],
                    'image_path': meta['root']
                })
        elif isinstance(filepath, dict):
            if "annotation" in filepath.keys():
                input_list.append({
                    'text_file': filepath['annotation'],
                    'image_path': filepath['root']
                })
            else:
                for k, v in filepath:
                    input_list.append({
                        'text_file': v['annotation'],
                        'image_path': v['root']
                    })
        elif isinstance(filepath, list):
            for meta in filepath:
                input_list.append({
                    'text_file': meta['annotation'],
                    'image_path': meta['root']
                })
        
        print(f"检查{len(input_list)}个数据集")
        self._checkdata(input_list)