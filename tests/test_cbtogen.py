import pytest

import osmdigest.utils.cbtogen as cbtogen


# Example function which sends data to a callback function
def push_data_to_callback(callback):
    for x in "abcd":
        callback.send_letter(x)
    for x in "1234":
        callback.send_number(int(x))
        
# Example "handler" which wraps the data 
class OurHandler():
    def __init__(self, delegate):
        self.delegate = delegate
        
    def send_letter(self, x):
        self.delegate.send("letter", x)

    def send_number(self, x):
        self.delegate.send("number", x)


def test_generator():
    gen = cbtogen.CallbackToGenerator()
    gen.set_handler(push_data_to_callback, OurHandler(gen))
    
    out = []
    with gen:
        for x in gen:
            out.append(x)
            
    assert(len(out) == 8)
    for d, expected in zip(out[:4], "abcd"):
        assert(d.name == "letter")
        assert(d.data == expected)
    for d, expected in zip(out[4:], [1,2,3,4]):
        assert(d.name == "number")
        assert(d.data == expected)

def test_generator_alternative_setup():
    gen = cbtogen.CallbackToGenerator()
    def provider_func():
        push_data_to_callback(OurHandler(gen))
    gen.set_callback_function(provider_func)
    
    out = []
    with gen:
        for x in gen:
            out.append(x)
            
    assert("".join(str(d.data) for d in out) == "abcd1234")

class OurException(Exception):
    def __init__(self, message):
        super().__init__(message)

# Example function which sends data to a callback function
# but which raises an Exception at some point
def push_data_to_callback_throws(callback):
    for x in "abcd":
        callback.send_letter(x)
    raise OurException("Oh no!")
        
        
def test_generator_with_exception_from_data_provider():
    gen = cbtogen.CallbackToGenerator()
    gen.set_handler(push_data_to_callback_throws, OurHandler(gen))
    
    with pytest.raises(OurException):
        # The exception should be returned to us
        with gen:
            list(gen)

# A class which provides data.  Should how we can catch the EarlyTerminate
# exception to detect when no more data is required.
class DataProvider():
    def __init__(self):
        self.count = 0
        self.was_stopped = False
        
    def process(self, callback):
        try:
            for x in "abcd":
                callback.send_letter(x)
                self.count += 1
            for x in "1234":
                callback.send_number(int(x))
                self.count += 1
        except cbtogen.EarlyTerminate:
            self.was_stopped = True

def test_generator_stopped_provider_ended():
    gen = cbtogen.CallbackToGenerator(queuesize=1)
    provider = DataProvider()
    gen.set_handler(provider.process, OurHandler(gen))
    
    out = []
    with gen:
        for i, x in zip(range(4), gen):
            out.append(x)
            
    assert(len(out) == 4)
    assert(provider.count == 5)
    assert(provider.was_stopped)