import types

import DateTime
from OFS.OrderedFolder import OrderedFolder

from Products.XWFCore.XWFCatalogAware import XWFCatalogAware
from Products.XWFIdFactory.XWFIdFactoryMixin import XWFIdFactoryMixin
from Products.CustomProperties.CustomProperties import CustomProperties

from AccessControl import ClassSecurityInfo
from zope.interface import implements
from interfaces import IXWFDataObject

from XWFContentObject import XWFContentObject #@UnusedImport - used externally

import logging
log = logging.getLogger()

class XWFDataContainer(OrderedFolder, XWFIdFactoryMixin):
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    
    meta_type = "XWF Data Container"
    
    version = 0.1
    
    security_management = () # Must be set in subclasses
    data_definition = () # Must be set in subclasses
    id_namespace = None # Must be set in subclasses
    
    def __init__(self, id):
        self.__name__ = id
        self.id = id
        
    def get_filteredDataDefinition(self):
        return filter(lambda x: not x.automatic, self.data_definition)
    
    def reindex_data_objects(self):
        """ Reindex all the data objects that we contain.
        
        """
        count = 0
        for defn in self.data_definition:
            # force the setup in the catalog
            defn.setup_catalog(self, True)
        for object in self.aq_explicit.objectValues():
            if getattr(object, 'isDataObject', False):
                object.reindex_object()
                count += 1
                
        return count
    
    def data_object_factory(self):
        """ A generic method for returning an instance of XWFDataObject, or
            its subclass.
        
            This must be overridden in subclasses.
            
        """
        return XWFDataObject(self.get_nextId())
    
    def modify_data_object(self, **kws):
        """ Modify a data object. This is primarily a hook for modifying a data
            object, by default it just checks to see that we have everything we
            need to get the object (ie. that we have the ID).
        
        """
        if kws.get('id', None) and hasattr(self.aq_explicit, kws['id']):
            return self.create_data_object(**kws)
        else:
            raise AttributeError, 'No such data object, ID %s' % kws['id']
        
    def create_data_object(self, **kws):
        """ A generic method for creating/adding/modifying a data object. We
            iterate through the kws looking for two things:
                
            1) any metadata we know we need
            2) the 'data' segment, assumed to be a file object, or something else.
            
            If we are passed a non-empty 'id' in the keywords, we assume that
            we're really modifying an object.
            
        """
        # if we have been passed an id, it's because we're performing
        # a modification
        existing_id = kws.get('id', None)
        if existing_id:
            obj = getattr(self.aq_explicit, existing_id)
        else:
            obj = self.data_object_factory()
                
        for defn in self.data_definition:
            indexName = defn.indexName
            dataType = defn.propertyDataType
            defn.setup_catalog(self)
            if defn.automatic:
                if defn.setDefault:
                    if callable(defn.default):
                        default = defn.default()
                    else:
                        default = defn.default
                    obj.add_change_property(indexName, default, dataType)
                else:
                    # TODO: we need to handle the _non_ default case!
                    pass
            elif kws.has_key(indexName):
                val = kws.get(indexName)
                obj.add_change_property(indexName, val, dataType)
                # it's also possible that this object has other names,
                # for instance, dc_title is also known as title
                for altIndex in getattr(defn, 'alternativeIndexNames', []):
                    obj.add_change_property(altIndex, val, dataType)
        
        # find and insert the data, if it exists
        for key in kws:
            if key == 'data':
                if type(kws[key]) == types.FileType:
                    obj.set_content(file.read())
                else:
                    obj.set_content(kws[key])
        
        # don't create the object again if the object already exists!
        if not existing_id:
            self.aq_explicit._setObject(obj.getId(), obj)
        new_object = getattr(self.aq_explicit, obj.getId())
        
        # look for any security management requests in the form
        for sec in self.security_management:
            # it is up to the validation framework to determine if we can
            # get this far
            vals = kws.get(sec.id, [])
            if type(vals) == types.StringType:
                vals = [vals]
            sec.set_permissions(new_object, vals)
            new_object.reindexObjectSecurity()
                
        return True
        
    def manage_afterAdd(self, item, container):
        for item in self.data_definition:
            item.setup_catalog(self)

def addedDataObject(ob, event):
    """A DataObject was added to the storage.

    """
    log.info('Added data object')
    ob.index_object()
    
class XWFDataObject(XWFCatalogAware, CustomProperties):
    implements(IXWFDataObject)
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
    
    meta_type = 'XWF Data Object'
    
    isDataObject = True
    
    content = ''
    _modification_time = None
    def __init__(self, id, title=None):
        self.id = id
        self.content = ''
        
        CustomProperties.__init__(self, id, title)
    
        self.set_modification_time()
    
    def get_propertiesAsDict(self):
        """ """
        d = {}
        for id, val in self.propertyItems():
            d[id] = val
        d['modification_time'] = self.modification_time()
        d['indexable_content'] = self.indexable_content()
        d['indexable_summary'] = self.indexable_summary()
        d['id'] = self.id
        
        return d
    
    # just a convenience method
    def add_change_property(self, name, value, _type):
        """ Add or change a property, depending if it exists or not.
        
        """
        if self.hasProperty(name):
            self.manage_changeProperties(**{name: value})
        else:
            self.manage_addProperty(name, value, _type)
            
        self.set_modification_time()
    
    def set_content(self, content):
        self.content = content
    
    def set_modification_time(self):
        self._modification_time = DateTime.DateTime()
        
    def modification_time(self):
        return self._modification_time
       
    def indexable_content(self):
        return self.content
    
    def indexable_summary(self):
        return self.content[:200]
    
    def manage_beforeDelete(self, item, container):
        """ For cleaning up as we are removed.

        """
        CustomProperties.manage_beforeDelete(self, item, container)
        XWFCatalogAware.manage_beforeDelete(self, item, container)
        
    def manage_afterClone(self, item):
        """ For configuring the object post move or copy.

        """
        CustomProperties.manage_afterClone(self, item)
        XWFCatalogAware.manage_afterClone(self, item)
        
