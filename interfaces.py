from zope.interface import Interface, Attribute

class IXWFDataObject(Interface):
    def get_propertiesAsDict():
        """ """

    def add_change_property(name, value, type):
        """ Add or change a property, depending if it exists or not.

        """

class IXWFContentObject(Interface):
    """ A Content Object is a container for editable content, which is 
        automatically indexed.

    """
