def deco_func_i2c_channel0(func, cmd):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Yep, its global. I found no satisfactory way to add an argument to the decorator
        # self.i2c_mux(0)          
        cmd()
        return func(*args, **kwargs)
    return wrapper

def deco_func_i2c_channel1(func, cmd):
    @wraps(func)
    def wrapper(*args,**kwargs):
        cmd()          
        return func(*args, **kwargs)
    return wrapper
