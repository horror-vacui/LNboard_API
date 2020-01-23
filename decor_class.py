from functools import wraps, partial
import inspect, types

def deco_func(func): #, channel):      
    @wraps(func)
    def new_function(*args,**kwargs):
        print("Decorator func.")
        return func(*args,**kwargs)                
    return new_function  

if False:
    print("checking the operation of the decorator function")
    def sq(a):
        print(a**2)
    sq2 = deco_func(sq)
    sq(1.1)
    sq2(1.3) # yep, sq2 works


class my_class():
    def __init__(self, a):
        self.a = a
    def square(self):
        self.a = self.a**2
        print(self.a)

class my_subclass(my_class):
    def __init__(self, func, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # go over all elements in my_class and if it is callable, apply the
        # decorator function
        for attr_name in my_class.__dict__:
            attr = getattr(self, attr_name)
            if callable(attr) and attr_name[0:2] != "__":
                print("Callable method found: %r" % attr_name)
                setattr(self, attr_name, partial(func, attr))

class my_subclass2(my_class):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # go over all elements in my_class and if it is callable, apply the
        # decorator function
        for attr_name in my_class.__dict__:
            attr = getattr(self, attr_name)
            if callable(attr) and attr_name[0:2] != "__":
                print("Callable method found: %r" % attr_name)
                setattr(self, attr_name, deco_func(attr))

# https://stackoverflow.com/a/3467879/1424118
# edited since then


class my_subclass3(my_class):
    pass


print("\nOriginal class:")
a = my_class(1.05)
a.square()
a.square()

print("Supposed to be 1.05^4: %r" % a.a)
print("\nFirst subclass version:")
b = my_subclass(a=1.07, func=deco_func)
b.square()
b.square()
print("Supposed to be 1.07^4: %r" % b.a)
print("\nSecond subclass version:")
c = my_subclass2(a=1.03)
c.square()
c.square()
print("Supposed to be 1.03^4: %r" % c.a)

print("\nThird subclass version:")
d = my_subclass3(a=1.01)
print(f"a.a={a.a}")
print(d.a)
for method_name in dir(a):
    if method_name[0:2] != "__":
        fn = getattr(a,method_name)
        if callable(fn):
            setattr(d, method_name, deco_func(fn))
print(d.a)

d.square()
d.square()
print("Supposed to be 1.01^4: %r" % d.a)
print(f"a.a={a.a}")
# d.square()
# d.square()
# print("Supposed to be 1.01^4: %r" % d.a)
