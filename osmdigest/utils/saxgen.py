"""
saxgen
~~~~~~

Converts the `xml.sax` module into a python generator.

Typical use case is:
    
    with saxgen.parse("filename.xml") as generator:
        for event in generator:
            # Process event which is a subtype of SAXEvent
            pass

"""

from . import cbtogen
import xml.sax

class SAXEvent():
    """Base class for all XML "events", as would be sent to
    :class:`xml.sax.handler.ContentHandler`."""
    def __init__(self, event, data):
        self._event = event
        self._data = data
        
    @property
    def event(self):
        """The name of the XML event.  Same as the method name from
        :class:`xml.sax.handler.ContentHandler`.
        """
        return self._event
    
    @property
    def data(self):
        """The data associated with the event.  May be `None`, as single
        object, or a tuple, as appropriate.
        """
        return self._data
    
    def __repr__(self):
        if self.data is None:
            return "SAXEvent('{}')".format(self.event)
        return "SAXEvent('{}'->{})".format(self.event, self.data)

    def __eq__(self, other):
        return self.event == other.event and self.data == other.data

    
class StartDocument(SAXEvent):
    def __init__(self):
        super().__init__("startDocument", None)

        
class EndDocument(SAXEvent):
    def __init__(self):
        super().__init__("endDocument", None)


class StartPrefixMapping(SAXEvent):
    def __init__(self, prefix, uri):
        super().__init__("startPrefixMapping", (prefix, uri))
    
    @property
    def prefix(self):
        return self.data[0]
    
    @property
    def uri(self):
        return self.data[1]


class EndPrefixMapping(SAXEvent):
    def __init__(self, prefix):
        super().__init__("endPrefixMapping", prefix)
    
    @property
    def prefix(self):
        return self.data


class StartElement(SAXEvent):
    def __init__(self, name, attrs):
        attrs_dict = {key : attrs[key] for key in attrs.keys()}
        super().__init__("startElement", (name, attrs_dict))
    
    @property
    def name(self):
        return self.data[0]
    
    @property
    def attrs(self):
        return self.data[1]


class EndElement(SAXEvent):
    def __init__(self, name):
        super().__init__("endElement", name)
    
    @property
    def name(self):
        return self.data


class StartElementNS(SAXEvent):
    def __init__(self, name, qname, attrs):
        attrs_dict = {key : attrs[key] for key in attrs.keys()}
        super().__init__("startElementNS", (name, qname, attrs_dict))
    
    @property
    def name(self):
        return self.data[0]
    
    @property
    def qname(self):
        return self.data[1]

    @property
    def attrs(self):
        return self.data[2]


class EndElementNS(SAXEvent):
    def __init__(self, name, qname):
        super().__init__("endElementNS", (name, qname))
    
    @property
    def name(self):
        return self.data[0]
    
    @property
    def qname(self):
        return self.data[1]


class Characters(SAXEvent):
    def __init__(self, content):
        super().__init__("characters", content)
    
    @property
    def content(self):
        return self.data


class IgnorableWhitespace(SAXEvent):
    def __init__(self, whitespace):
        super().__init__("IgnorableWhitespace", whitespace)
    
    @property
    def whitespace(self):
        return self.data

 
class ProcessingInstruction(SAXEvent):
    def __init__(self, target, data):
        super().__init__("processingInstruction", (target, data))
    
    @property
    def target(self):
        return self.data[0]

    @property
    def dataa(self):
        return self.data[1]


class SkippedEntity(SAXEvent):
    def __init__(self, name):
        super().__init__("skippedEntity", name)
    
    @property
    def name(self):
        return self.data


class _Handler(xml.sax.handler.ContentHandler):
    def __init__(self, delegate):
        self.delegate = delegate
    
    def startDocument(self):
        self.delegate.notify(StartDocument())
        
    def endDocument(self):
        self.delegate.notify(EndDocument())
        
    def startPrefixMapping(self, prefix, uri):
        self.delegate.notify(StartPrefixMapping(prefix, uri))
        
    def endPrefixMapping(self, prefix):
        self.delegate.notify(EndPrefixMapping(prefix))
        
    def startElement(self, name, attrs):
        self.delegate.notify(StartElement(name, attrs))
        
    def endElement(self, name):
        self.delegate.notify(EndElement(name))
        
    def startElementNS(self, name, qname, attrs):
        self.delegate.notify(StartElementNS(name, qname, attrs))

    def endElementNS(self, name, qname):
        self.delegate.notify(EndElementNS(name, qname))

    def characters(self, content):
        self.delegate.notify(Characters(content))

    def ignorableWhitespace(self, whitespace):
        self.delegate.notify(IgnorableWhitespace(whitespace))
        
    def processingInstruction(self, target, data):
        self.delegate.notify(ProcessingInstruction(target, data))

    def skippedEntity(self, name):
        self.delegate.notify(SkippedEntity(name))


def parseString(stringData):
    """As `xml.sax.parseString` but as a context-manager giving a generator 
    which will yield sub-types of :class:`SAXEvent`
    """
    generator = cbtogen.CallbackToGenerator()
    def func():
        xml.sax.parseString(stringData, _Handler(generator))
    generator.set_callback_function(func)
    return generator


def parse(fileObject):
    """As `xml.sax.parse` but as a context-manager giving a generator  which
    will yield sub-types of :class:`SAXEvent`
    """
    generator = cbtogen.CallbackToGenerator()
    def func():
        xml.sax.parse(fileObject, _Handler(generator))
    generator.set_callback_function(func)
    return generator
