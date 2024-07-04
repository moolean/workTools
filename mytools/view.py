
import nbformat as nbf

def startView(data_jsonl="", images_root=""):
    '''
    创建ipynb文件来看数据，当前代码只创建代码文件，输入可以为空
    '''
    # 创建一个新的 notebook 对象
    nb = nbf.v4.new_notebook()

    # 添加代码单元格
    code1 = """
import ipywidgets as widgets
from IPython.display import display, clear_output
from utils.datavisulize import displayPerData

def displayData(data_list, current_index):
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
        img = displayPerData(data_list[current_index])
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
            img = displayPerData(data_list[current_index])
            display(img)
    
    # 绑定按钮的点击事件
    button_prev.on_click(on_button_clicked)
    button_next.on_click(on_button_clicked)
    """
    code2 = f"""
from mytools import read_jsonl
dataroot = "{images_root}"
data_jsonl = "{data_jsonl}"
data = read_jsonl(data_jsonl)
current_index = 0  # 当前数据索引
displayData(data, current_index)
    """

    nb.cells.append(nbf.v4.new_code_cell(code1))
    nb.cells.append(nbf.v4.new_code_cell(code2))

    # 保存 notebook 到文件
    with open('view.ipynb', 'w') as f:
        nbf.write(nb, f)

    print("Notebook created successfully!")
