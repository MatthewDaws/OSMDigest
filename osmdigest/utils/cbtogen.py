"""
cbtogen
~~~~~~~

Simple thread-based code which can convert a call-back style data generation
pattern to a generator style pattern.

Sample use case is to consume data from `xml.sax.parse`.  This function takes
a callback object to which all the parsed XML data is sent.  By using the
classes in this module, we can automatically spin up a separate thread which
calls the `parse` function and which writes the data to a queue.  The consumer
code can consume this data from a Python generator without worrying about the
threading code.
"""

import threading, queue

class EarlyTerminate(Exception):
    """Raised to indicate that we do not require any further data and that,
    if possible, the provider of data should cleanup and exit."""
    pass
    

class CallbackToGenerator():
    """Gives a Context Manager which returns a generator which yields the data
    sent to the callback.
    
    Start with a data provider which sends data to a callback object.  You
    should write your own callback object which forwards on the data to the
    :method:`send` method of this class.  Then call :method:`set_handler` with
    the data provider and your callback.  Hence:
        
        class HandlerInterface():
            def one(self, data):
                pass
                
            def two(self, data):
                pass
                
        class OurHandler(HandlerInterface):
            def __init__(self, delegate):
                self._delegate = delegate
                
            def one(self, data):
                self._delegate.send("one", data)

            def two(self, data):
                self._delegate.send("two", data)
        
        # Normal usage of the data provider:
        handler = HandlerInterface()
        provider(handler)
        # The `handler` gets pushed the data as a callback
        
        # Usage of this class to provider a generator
        generator = cbtogen.CallbackToGenerator()
        handler = OurHandler(generator)
        generator.set_handler(provider, handler)
        
        with generator:
            for x in generator:
                # x is of type Wrapper
                print("Got {} / {}".format(x.name, x.data))
                
        # Use of "with" ensures that if an exception is thrown, the thread
        # is automatically closed.
    """
    def __init__(self, queuesize=65536):
        self._queue = queue.Queue(maxsize=queuesize)
        self._terminate = False
    
    def notify(self, data):
        """Notify of some data.  Your callback handler should, after possible
        processing, push data to this method.  Can accept any data, but if
        you notify of an :class:`Exception` then the exception will be raised
        by the iterator; if you notify with the `StopIteration` type then the
        iterator will stop (but the *strongly* preferred way to end iteration
        is to let the callback thread end.)
        
        Will raise an exception of type :class:`EarlyTerminate` to signal that
        data generation should be stopped.
        
        :param data: The data object to add to the internal queue.
        """
        if self._terminate:
            self._queue.put(StopIteration)
            raise EarlyTerminate()
        self._queue.put(data)
    
    def send(self, name, data):
        """Standardised way to send data.  The iterator will yield an instance
        of :class:`Wrapper` with the `name`/`data` pair.
        
        :param name: Name of the callback event which generated this data.
        :param data: Tuple of data, or `None`.
        """
        self.notify(Wrapper(name, data))
    
    def __enter__(self):
        def ourtask():
            try:
                self._func()
            except Exception as ex:
                self._queue.put(ex)
            self._queue.put(StopIteration)
        self._thread = threading.Thread(target=ourtask)
        self._thread.start()
        return iter(self)
    
    def __exit__(self, type, value, traceback):
        self._terminate = True
        while self._thread.is_alive():
            try:
                self._queue.get(timeout=0.1)
            except queue.Empty:
                pass
    
    def __iter__(self):
        while True:
            try:
                datum = self._queue.get(timeout=1)
                if datum is StopIteration:
                    break
                if isinstance(datum, Exception):
                    raise datum
                yield datum
            except queue.Empty:
                if not self._thread.is_alive():
                    break

    def set_callback_function(self, func):
        """Set the function to invoke on a seperate thread to generate data.
        See also :method:`set_handler` which can be more useful.
        
        :param func: A callable object (i.e. a function object which can be
        invoked with no parameters).
        """
        self._func = func
        
    def set_handler(self, func, handler):
        """Set the function to invoke on a separate thread to generate data.
        
        :param func: A callable object with signature `func(handler)`.
        :param handler: The handler object of the type expected by `func`.
        """
        def routine():
            func(handler)
        self.set_callback_function(routine)
        

class Wrapper():
    """Standard way to wrapping the result of a callback into a "name" and a
    tuple of "data".
    
    :param name: String name to identify which callback method was invoked.
      Typically just the name of the callback method.
    :param data: The wrapped data, or `None`.
    """
    def __init__(self, name, data=None):
        self._name = name
        self._data = data
        
    @property
    def name(self):
        """The name of the callback event which received the data."""
        return self._name
    
    @property
    def data(self):
        """The wrapped data, typically an object, a tuple, or `None`."""
        return self._data