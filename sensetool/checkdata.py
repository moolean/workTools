
import json
from pathlib import Path
import random
import re
import traceback
import time, os
import pandas as pd
import concurrent.futures
from .basic import get_image
from .jsonl import read_jsonl
from collections import defaultdict

# def check_format(dataset):
#     for index, data in enumerate(dataset):
#         # if 'image' in data and data['image'] is not None:
#         #     if 'width' not in data or 'height' not in data:
#         #         return f"index={index}, no width or height"
#         #     if not (isinstance(data['width'], int) and data['width'] > 0):
#         #         return f'index={index}, data["width"] = ({type(data["width"])}) {data["width"]}'
#         #     if not (isinstance(data['height'], int) and data['height'] > 0):
#         #         return f'index={index}, data["height"] = ({type(data["height"])}) {data["height"]}'
#         if len(data['conversations']) < 2 or len(data['conversations']) % 2 != 0:
#             return f"index={index}, Not correct number: {index}"
#         for i, message in enumerate(data['conversations']):
#             if i == 0:
#                 if not message['value'].startswith('<image>\n'):
#                     return f"index={index}, No <image> tag: {index}, {message['value']}"
#             if i > 0:
#                 if '<image>' in message['value']:
#                     return f"index={index}, extra <image> tag: {index}"
#             if not isinstance(message['value'], str):
#                 return f"index={index}, Not correct format: it should be a string: {index}"
#             if not (len(message['value']) > 0):
#                 return f"index={index}, No Message: {data}: {index}"
#             if i % 2 == 0:
#                 if not (message['from'] == 'human'):
#                     return f"index={index}, Not from human: {data}: {index}"
#             else:
#                 if not (message['from'] == 'gpt'):
#                     return f"index={index}, Not from gpt: {data}: {index}"

markdown_pattern = r'```markdown\n(.*?)\n```'
compiled_markdown_pattern = re.compile(markdown_pattern, re.DOTALL)
markdown_table_pattern = r'\|\s*\n\s*\|'
compiled_markdown_table_pattern = re.compile(markdown_table_pattern)

grounding_pattern = r'<ref>(.*?)</ref><box>(.*?)</box>'
compiled_grounding_pattern = re.compile(grounding_pattern)

ocr_wbox_pattern = r'<ref>(.*?)</ref><box>(.*?)</box>(.*?)(?=<ref>|$)'
compiled_ocr_wbox_pattern = re.compile(ocr_wbox_pattern, re.DOTALL)

csv_pattern = r'```csv\n.*?\n```'
compiled_csv_pattern = re.compile(csv_pattern, re.DOTALL)



# ```markdown\n{content}\n```中的content必须含有表格，markdown表格至少包含4个|和3个-
def check_markdown(answer, invalid_types):
    match_results = compiled_markdown_pattern.findall(answer)
    for table_content in match_results:
        if not compiled_markdown_table_pattern.search(table_content) or table_content.count('|') < 4 or table_content.count('-') < 3:
            invalid_types.add("wrong_markdown_pattern")
            return


def check_grounding(answer, invalid_types):
    match_results = compiled_grounding_pattern.findall(answer)

    for ref_content, box_content in match_results:
        try:
            assert ref_content.strip()
            bbox_list = eval(box_content)
            assert isinstance(bbox_list, list)
            for bbox in bbox_list:
                assert isinstance(bbox, list)
                assert len(bbox) == 4
                assert all(0<=num<=1000 for num in bbox)
        except Exception:
            invalid_types.add("wrong_grounding_pattern")
            return


def check_ocr_wbox(answer, invalid_types):
    match_results = compiled_ocr_wbox_pattern.findall(answer)

    for idx, (ref_content, box_content, separator) in enumerate(match_results):
        try:
            assert ref_content.strip()
            bbox_list = eval(box_content)
            assert isinstance(bbox_list, list)
            for bbox in bbox_list:
                assert isinstance(bbox, list)
                assert len(bbox) == 4
                assert all(0<=num<=1000 for num in bbox)
            # 最后一个</box>后就不管是什么了，正常情况似乎answer应该以</box>为结尾
            assert separator == "\n\n" or idx == len(match_results) - 1
        except Exception:
            invalid_types.add("wrong_ocr_wbox_pattern")
            return


def check_latex(answer, invalid_types):
    last_delimiter = ""
    latex_commands = ['\\int', '\\frac', '\\sum', '\\sin', '\\cos', '\\sqrt', '\\begin', '\\end', '\\left', '\\right']
    for i in range(len(answer)):
        # latex包裹不能嵌套
        if answer[i:i+8] == "```latex":
            if last_delimiter or i+8 == len(answer) or answer[i+8] != "\n":
                invalid_types.add("wrong_latex_pattern")
                return
            else:
                last_delimiter = "```latex\n"
            i += 9
        # 可能存在多个其他种类的代码块，避免风险就不检查了，情况比较复杂，出了问题再说
        elif answer[i:i+4] == "\n```":
            last_delimiter = ""
            i += 1
            # if last_delimiter == "```latex\n":
            #     last_delimiter = ""
            # else:
            #     invalid_types.add("wrong_latex_pattern")
            #     return
        elif answer[i:i+2] == '\\(':
            if last_delimiter:
                invalid_types.add("wrong_latex_pattern")
                return
            else:
                last_delimiter = "\\("
            i += 2
        elif answer[i:i+2] == '\\)':
            if last_delimiter == "\\(":
                last_delimiter = ""
            else:
                invalid_types.add("wrong_latex_pattern")
                return
            i += 2
        elif answer[i:i+2] == '\\[':
            if last_delimiter:
                invalid_types.add("wrong_latex_pattern")
                return
            else:
                last_delimiter = "\\["
            i += 2
        elif answer[i:i+2] == '\\]':
            if last_delimiter == "\\[":
                last_delimiter = ""
            else:
                invalid_types.add("wrong_latex_pattern")
                return
            i += 2
        # 必须在被latex包裹环境中才能使用latex命令
        elif any(answer[i:i+len(command)] == command for command in latex_commands):
            if last_delimiter == "":
                invalid_types.add("wrong_latex_pattern")
                return
            i += 1
        else:
            i += 1
    
    # 检查是否有未闭合的分隔符
    if last_delimiter:
        invalid_types.add("wrong_latex_pattern")
    
# 必须存在```csv\n{content}\n```这样的pattern
def check_csv(answer, invalid_types):
    if not compiled_csv_pattern.search(answer):
        invalid_types.add("csv_pattern not exist")

def check_answer(answer, invalid_types, format_tag):
    format_tag_list = format_tag.split(",")
    # 无论什么数据集都需要进行的答案格式校验
    check_markdown(answer, invalid_types)


    if "OCR_wBox" in format_tag_list:
        check_ocr_wbox(answer, invalid_types)
    elif "grounding" in format_tag_list:
        check_grounding(answer, invalid_types)
    elif "math" in format_tag_list:
        check_latex(answer, invalid_types)
    elif "csv" in format_tag_list:
        check_csv(answer, invalid_types)


def check_conversations(sample, invalid_types, format_tag, modal_placeholder=None):
    modal_placeholder_num = 0
    if 'conversations' not in sample or sample['conversations'] is None or len(sample['conversations']) == 0:
        invalid_types.add("no conversations")
    else:
        for turn, message in enumerate(sample['conversations']):
            valid_message_value_flag = False
            # check message value
            if "value" not in message or message['value'] is None or len(message['value']) == 0:
                invalid_types.add(f'empty {message.get("from", "role")} message value')
            else:
                valid_message_value_flag = True
                
            # check message role
            if "from" not in message or message['from'] is None or len(message['from']) == 0:
                invalid_types.add(f"empty message role")
            else:
                if message['from'] == 'system':
                    # 必须是第一轮，且不能是最后一轮，后面一轮必定是human
                    if turn != 0 or turn+1 == len(sample['conversations']):
                        invalid_types.add("wrong conversation sequence")
                elif message['from'] == 'human':
                    # 不能是最后一轮，且后面一轮必须是gpt
                    if turn+1 == len(sample['conversations']) or sample['conversations'][turn+1]['from'] != "gpt":
                        invalid_types.add("wrong conversation sequence")
                    if valid_message_value_flag and modal_placeholder:
                        modal_placeholder_num += message['value'].count(modal_placeholder)
                elif message['from'] == 'gpt':
                    # 不能是第一轮，且前面一轮必须是human
                    if turn-1 < 0 or sample['conversations'][turn-1]['from'] != "human":
                        invalid_types.add("wrong conversation sequence")
                    if valid_message_value_flag:
                        check_answer(message['value'], invalid_types, format_tag)
                else:
                    invalid_types.add("unexpected message role")
                
    return modal_placeholder_num

def check_language_sample(sample, invalid_types, format_tag):
    if sample['conversation'] is None or len(sample['conversation']) == 0:
        invalid_types.add("no conversation")
    else:
        for message in sample['conversation']:
            if "input" not in message or message['input'] is None or len(message['input']) == 0:
                invalid_types.add("empty input message")
            
            if "output" not in message or message['output'] is None or len(message['output']) == 0:
                invalid_types.add("empty output message")
            else:
                check_answer(message['value'], invalid_types, format_tag)


def check_image_input_sample(sample, invalid_types, format_tag, check_wh=True):
    # check conversations
    num_image = check_conversations(sample, invalid_types, format_tag, modal_placeholder="<image>\n")

    if sample['image'] is None or sample['image'] == "":
        invalid_types.add("no image")
    else:
        # check <image>\n num
        if type(sample['image']) is str:
            if num_image != 1:
                invalid_types.add("wrong image number")
        elif type(sample['image']) is list:
            if num_image != len(sample['image']):
                invalid_types.add("wrong image number")
        else:
            invalid_types.add("image field type error")


        # check wh field
        if check_wh:
            if 'width' not in sample or 'height' not in sample:
                invalid_types.add("wrong height/width")
            else:
                if type(sample['image']) is str:
                    if type(sample['width']) is not int or type(sample['height']) is not int or sample['width'] <= 0 or sample['height'] <=0:
                        invalid_types.add("wrong height/width")

                elif type(sample['image']) is list:
                    if type(sample['width']) is not list or type(sample['height']) is not list:
                        invalid_types.add("wrong height/width")
                    else:
                        if any(x <= 0 for x in sample['width']):
                            invalid_types.add("wrong height/width")
                        elif any(x <= 0 for x in sample['height']):
                            invalid_types.add("wrong height/width")
            

def check_video_input_sample(sample, invalid_types, format_tag):
    # check conversations
    num_video = check_conversations(sample, invalid_types, format_tag, modal_placeholder="<video>\n")

    # check video field
    if sample['video'] is None or sample['video'] == "":
        invalid_types.add("no video")
    elif type(sample['video']) is not str:
        invalid_types.add("video field type error")
    # check <video>\n num
    else:
        if num_video != 1:
            invalid_types.add("wrong video number")


def check_pure_text_sample(sample, invalid_types, format_tag):
    # check conversations
    check_conversations(sample, invalid_types, format_tag)


def check_dataset_format(dataset, format_tag="", check_wh=False):
    invalid_type2idx = defaultdict(list)
    for idx, sample in enumerate(dataset):
        try:
            invalid_types = set()
            if "conversation" in sample:
                check_language_sample(sample, invalid_types, format_tag)
            elif 'image' in sample:
                check_image_input_sample(sample, invalid_types, format_tag, check_wh=check_wh)
            elif 'video' in sample:
                check_video_input_sample(sample, invalid_types, format_tag)
            else:
                check_pure_text_sample(sample, invalid_types, format_tag)

            if invalid_types:
                for invalid_type in invalid_types:
                    invalid_type2idx[invalid_type].append(idx)

        except Exception as e:
            print(f"{type(e).__name__}: {e}")
            traceback.print_exc()
            invalid_type2idx["unknown error"].append(idx)

    return invalid_type2idx


def check_image_correct(dataset, image_root, client):
    cnt_fail = 0
    cnt_success = 0
    ret = True
    for data in dataset:
        if 'image' not in data:
            continue
        image_name = data['image']
        image_file = os.path.join(image_root, image_name)
        try:
            image = get_image(image_file, client)
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

def worker_fn(meta):
    # meta, client = args
    try:
        json_file = meta['text_file']
        image_root = meta['image_path']
        # print(f'>>> input={json_file}')
        dataset = read_jsonl(json_file, AossClient)
        # print(f'number={len(dataset)}')
        msg = check_dataset_format(dataset)
        # msg = None
        if msg == defaultdict(list):
            # return "sesecore cannot access mst images, other format correct"
            mini_dataset = random.choices(dataset, k=10)
            if check_image_correct(mini_dataset, image_root, AossClient):
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


class checker():
    """数据检查
    """
    def __init__(self, client=None) -> None:
        """初始化

        Args:
            client (aossclient): ceph客户端
        """
        global AossClient 
        AossClient = client

    def _checkdata(self, meta_dataset):
        # args = [(meta, lambda x:self._AossClient) for meta in meta_dataset]
        with concurrent.futures.ProcessPoolExecutor(max_workers=max(50, len(meta_dataset))) as executor:
            for meta, msg in zip(meta_dataset, executor.map(worker_fn, meta_dataset)):
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
        或者直接传入metadata_dict的文件地址

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
                for k, v in filepath.items():
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
        else:
            print("当前格式输入不支持")
        print(f"检查{len(input_list)}个数据集")
        self._checkdata(input_list)