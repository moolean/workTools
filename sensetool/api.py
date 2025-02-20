import base64
import imghdr

def encode_base64(file_path):
    with open(file_path, "rb") as file:
        encoded_string = base64.b64encode(file.read())
    return encoded_string.decode("utf-8")


def openai_api(openai_client, 
                model: str, 
                sys_prompt: str, 
                text: str, 
                img_path: str = None) -> str:
    """
    调用OpenAI API的工具函数
    
    参数:

        openai_client: OpenAI客户端实例，初始化方式：
                        from openai import OpenAI
                        client = OpenAI(api_key="your-api-key")
        model(str): 模型名
        sys_prompt (str): 系统提示词，用于指导模型行为
        text (str): 用户输入的文本内容
        img_path (str, optional): 图片的base64编码字符串，默认为None
        
    返回:
        str: OpenAI API的响应结果
        
    示例:
        >>> from openai import OpenAI
        >>> client = OpenAI(api_key="your-api-key")
        >>> response = openai("你是一个助手", "你好", client)
        >>> print(response)
    """
    # 构建消息列表
    messages = [{"role": "system", "content": sys_prompt},
                {"role": "user", "content": text}]
    
    # 如果有图片，按照OpenAI协议以base64格式传入
    if img_path:
        image_type = imghdr.what(img_path)
        base64_image = encode_base64(img_path)
        messages.append({
            "role": "user", 
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"}}
            ]
        })
        
    # 调用OpenAI API
    response = openai_client.chat.completions.create(
        model=model,  # 使用支持图像的模型
        messages=messages
    )
    
    return response.choices[0].message.content

def test_openai():
    """
    测试openai函数是否正常工作
    
    示例:
        >>> test_openai()
        '测试通过'
    """
    # 模拟OpenAI客户端
    class MockClient:
        class chat:
            class completions:
                @staticmethod
                def create(model, messages):
                    return type('obj', (object,), {
                        'choices': [type('obj', (object,), {
                            'message': type('obj', (object,), {
                                'content': '测试通过'
                            })
                        })]
                    })
    
    # 创建模拟客户端
    mock_client = MockClient()
    
    # 测试文本模式
    result = openai_api(mock_client, "gpt-3.5-turbo", "测试系统提示", "测试文本")
    assert result == "测试通过", "文本模式测试失败"
    
    # 测试图片模式
    result = openai_api(mock_client, "gpt-4-vision-preview", "测试系统提示", "测试文本", "/mnt/afs/yaotiankuo/multimodal_reasoning/latex_render/aops_data_geometry/images/3.jpg")
    assert result == "测试通过", "图片模式测试失败"
    
    return "测试通过"

if __name__ == "__main__":
    print(test_openai())