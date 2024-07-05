
import time
import functools

def timer_decorator(func):
    """时间可视化装饰器，@timer_decorator放在函数上面就能在运行时打印运行时间

    Args:
        func (function): 需要测量时间的函数

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function {func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper