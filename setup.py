from setuptools import setup
setup(name='sensetool',
      version='0.4',
      description='work tools',
      url='https://github.com/moolean/workTools.git',
      author='yao tiankuo',
      author_email='yaotiankuo@sensetime.com',
      license='MIT',
      packages=['sensetool'],
      zip_safe=False,
      install_requires=[
        "opencv-python",
        "pandas",
        "numpy",
        "easydict",
        "nbformat",
        "dashscope",
        "ipywidgets",
        "openai",
        "boto3"
        # 添加更多的依赖项
    ],
    )
