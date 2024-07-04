from setuptools import setup
setup(name='mytools',
      version='0.1',
      description='work tools',
      url='https://github.com/moolean/workTools.git',
      author='yao tiankuo',
      author_email='yaotiankuo@sensetime.com',
      license='MIT',
      packages=['mytools'],
      zip_safe=False,
      install_requires=[
        "opencv-python",
        "pandas",
        "numpy",
        "easydict",
        "nbformat",
        # 添加更多的依赖项
    ],
    )