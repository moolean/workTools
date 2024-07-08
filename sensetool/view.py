
import os
import nbformat as nbf
from PIL import Image

def resize(image, base_short_side=512):
    # Get the current size of the image
    width, height = image.size
    if max(width, height) < base_short_side:
        return image

    # Determine the short side and calculate the scaling factor
    if width < height:
        scaling_factor = base_short_side / width
        new_width = base_short_side
        new_height = int(height * scaling_factor)
    else:
        scaling_factor = base_short_side / height
        new_height = base_short_side
        new_width = int(width * scaling_factor)

    # Resize the image while keeping the aspect ratio
    resized_image = image.resize((new_width, new_height))

    return resized_image

def displayPerData(jsondata, images_root):
    print(jsondata)
    print(jsondata["conversations"][0]["value"])
    print(jsondata["conversations"][1]["value"])

    image = Image.open(os.path.join(images_root, jsondata["image"]))
    image = resize(image, 448)
    return image


def startView(data_jsonl="", images_root="", opt_root=""):
    '''
    创建ipynb文件来看数据，当前代码只创建代码文件，输入可以为空
    opt_root 为输出文件的目录，默认为当前目录
    '''
    # 创建一个新的 notebook 对象
    nb = nbf.v4.new_notebook()

    # 添加代码单元格
    code1 = """
import ipywidgets as widgets
from IPython.display import display, clear_output
from sensetool.view import displayPerData

def displayData(data_list, current_index, images_root):
    # 创建显示数据的输出区域
    output = widgets.Output()
    
    # 创建两个按钮：上一个和下一个
    button_prev = widgets.Button(description="上一个")
    button_next = widgets.Button(description="下一个")
    
    # 显示按钮和输出区域
    display(button_prev, button_next, output)
    
    # 显示初始数据
    with output:
        clear_output(wait=True)
        print(current_index)
        img = displayPerData(data_list[current_index], images_root)
        display(img)
        
    # 定义按钮点击事件处理函数
    def on_button_clicked(b):
        global current_index
        if b.description == "上一个":
            current_index = (current_index - 1) % len(data_list)
        elif b.description == "下一个":
            current_index = (current_index + 1) % len(data_list)
        
        # 更新输出区域显示的数据
        with output:
            clear_output(wait=True)
            print(current_index)
            img = displayPerData(data_list[current_index], images_root)
            display(img)
    
    # 绑定按钮的点击事件
    button_prev.on_click(on_button_clicked)
    button_next.on_click(on_button_clicked)
    """
    code2 = f"""
from sensetool import read_jsonl
dataroot = "{images_root}"
data_jsonl = "{data_jsonl}"
data = read_jsonl(data_jsonl)
current_index = 0  # 当前数据索引
displayData(data, current_index, dataroot)
    """

    nb.cells.append(nbf.v4.new_code_cell(code1))
    nb.cells.append(nbf.v4.new_code_cell(code2))

    # 保存 notebook 到文件
    with open(os.path.join(opt_root, f"view_{data_jsonl.split('/')[-1].split('.')[0]}.ipynb"), 'w') as f:
        nbf.write(nb, f)

    print("Notebook created successfully!")
