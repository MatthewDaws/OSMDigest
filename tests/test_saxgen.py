import osmdigest.utils.saxgen as saxgen

example = """<?xml version="1.0"?>
<doc name="matt">
<para>Hello, world!</para>
</doc>"""

def test_SAXEvent():
    one = saxgen.SAXEvent("name", (1,"bc", {"name":"bob"}))
    assert(one.__repr__() == "SAXEvent('name'->(1, 'bc', {'name': 'bob'}))")
    two = saxgen.SAXEvent("name", (1,"bc", {"name":"bob"}))
    assert(one == two)
    three = saxgen.SAXEvent("name", None)
    assert(three.__repr__() == "SAXEvent('name')")
    assert(one != three)
    four = saxgen.SAXEvent("name1", 12)
    assert(one != three)
    assert(three != four)


def test__Handler():
    class Delegate():
        def __init__(self):
            self.last = None
            
        def notify(self, data):
            self.last = data
            
    delegate = Delegate()
    handler = saxgen._Handler(delegate)
    
    handler.startDocument()
    assert(delegate.last == saxgen.StartDocument())

    handler.endDocument()
    assert(delegate.last == saxgen.EndDocument())
        
    handler.startPrefixMapping("one", "two")
    assert(delegate.last == saxgen.StartPrefixMapping("one", "two"))
    assert(delegate.last.prefix == "one")
    assert(delegate.last.uri == "two")

    handler.endPrefixMapping(123)
    assert(delegate.last == saxgen.EndPrefixMapping(123))
    assert(delegate.last.prefix == 123)
        
    handler.startElement("bob", {"fish":"haddock"})
    assert(delegate.last == saxgen.StartElement("bob", {"fish":"haddock"}))
    assert(delegate.last.name == "bob")
    assert(delegate.last.attrs == {"fish":"haddock"})
        
    handler.endElement("dave")
    assert(delegate.last == saxgen.EndElement("dave"))
    assert(delegate.last.name == "dave")
    
    handler.startElementNS("bob", "qbob", {"spam":"foo"})
    assert(delegate.last == saxgen.StartElementNS("bob", "qbob", {"spam":"foo"}))
    assert(delegate.last.name == "bob")
    assert(delegate.last.qname == "qbob")
    assert(delegate.last.attrs == {"spam":"foo"})

    handler.endElementNS("bob", "qbob")
    assert(delegate.last == saxgen.EndElementNS("bob", "qbob"))
    assert(delegate.last.name == "bob")
    assert(delegate.last.qname == "qbob")

    handler.characters("content\n")
    assert(delegate.last == saxgen.Characters("content\n"))
    assert(delegate.last.content == "content\n")
    
    handler.ignorableWhitespace("\t\t  ")
    assert(delegate.last == saxgen.IgnorableWhitespace("\t\t  "))
    assert(delegate.last.whitespace == "\t\t  ")

    handler.processingInstruction("tar", "datum")
    assert(delegate.last == saxgen.ProcessingInstruction("tar", "datum"))
    assert(delegate.last.target == "tar")
    assert(delegate.last.dataa == "datum")

    handler.skippedEntity("bob")
    assert(delegate.last == saxgen.SkippedEntity("bob"))
    assert(delegate.last.name == "bob")


def check_expected_events(out):
    assert(isinstance(out[0], saxgen.StartDocument))
    assert(out[1] == saxgen.StartElement("doc", {"name":"matt"}))
    assert(out[2] == saxgen.Characters("\n"))
    assert(out[3] == saxgen.StartElement("para", {}))
    assert(out[4] == saxgen.Characters("Hello, world!"))
    assert(out[5] == saxgen.EndElement("para"))
    assert(out[6] == saxgen.Characters("\n"))
    assert(out[7] == saxgen.EndElement("doc"))
    assert(out[8] == saxgen.EndDocument())
    assert(len(out) == 9)
    

def test_parseString():
    with saxgen.parseString(example) as gen:
        out = list(gen)
    check_expected_events(out)
    
def test_parse():
    import io
    file = io.StringIO(example)
    with saxgen.parse(file) as gen:
        out = list(gen)
    check_expected_events(out)
