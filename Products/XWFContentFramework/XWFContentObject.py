# Copyright (C) 2003,2004 IOPEN Technologies Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# You MUST follow the rules in http://iopen.net/STYLE before checking in code
# to the trunk. Code which does not follow the rules will be rejected.
#
from AccessControl.ZopeGuards import guarded_getattr, guarded_hasattr
from Products.PageTemplates import PageTemplateFile
from OFS.OrderedFolder import OrderedFolder
from OFS.ObjectManager import ObjectManager
from OFS.SimpleItem import Item
from zope.interface import implements

from Products.XWFIdFactory.XWFIdFactoryMixin import XWFIdFactoryMixin
from interfaces import IXWFContentObject
from AccessControl import Role, ClassSecurityInfo

class TransformError(Exception):
    pass

def addedContentObject(obj, event):
    obj.set_resourceLocator()

class XWFContentObject(OrderedFolder, XWFIdFactoryMixin):
    implements(IXWFContentObject)
    
    security = ClassSecurityInfo()
    security.declareObjectProtected('View')
        
    meta_type = "XWF Content Object"
    
    version = 0.1
    
    manage_options = (ObjectManager.manage_options+
                      Role.RoleManager.manage_options+
                      Item.manage_options)
    
    id_namespace = 'http://iopen.net/namespaces/resources/locator'
    resource_locator = None

    content_container = None
    
    def __init__(self, id, title=None):
        """ Initialise a new instance of XWF Content Object.

        """
        self.__name__ = id
        if title:
            self.title = title
        else:
            self.title = id
            
        self.id = id
    
    security.declarePrivate('view_xform_data')
    def view_xform_data(self, datacont, model_id, submit_id, form):
        """ XForm data model view.
        
        """
        action = self.REQUEST.URL
        xform = '''<xf:model id="%(model_id)s">
                    <xf:instance>
                       <data>
                           <submitted/>
                           <id>%(form_id)s</id>
                           %(mid_xml)s
                       </data>
                    </xf:instance>
                    %(bind_xml)s
                    <xf:submission method="form-data-post"
                                   id="%(submit_id)s"'''+' action="%s"' % action+'''/>    
                  </xf:model>'''
        
        mid_xml = ''
        bind_xml = ''
        for obj in (datacont.get_filteredDataDefinition() +
                    datacont.security_management):
            if obj.meta_type == 'XWF Metadata':
                mid_xml += obj.xform_data(self, form)
            else:
                mid_xml += obj.xform_data(datacont, form)
            if obj.required:
                id = getattr(obj, 'indexName', None) or getattr(obj, 'id')
                bind_xml += ('<xf:bind id="%(id)s" nodeset="%(id)s" '
                                      'required="true()"/>' % locals())
                                      
        form_id = form.get('id', '')
        
        return xform % locals()
    
    security.declarePrivate('view_xform_control')
    def view_xform_control(self, datacont, model_id, submit_id, label, hint=None):
        """ XForm control view.
        
        """
        if not hint:
            hint = label
            
        xml = ''
        for obj in datacont.get_filteredDataDefinition():
            xml += '%s\n' % obj.xform_control(self, model_id)
        
        for obj in datacont.security_management:
            xml += '%s\n' % obj.xform_control(datacont, model_id)
        
        xml += '''<xf:submit model="%(model_id)s" submission="%(submit_id)s"
                             class="button" >
                      <xf:label>%(label)s</xf:label>
                      <xf:hint>%(hint)s</xf:hint>
                  </xf:submit>''' % locals()
        
        return xml
        
    security.declarePublic('get_resourceLocator')
    def get_resourceLocator(self):
        """ """
        return self.resource_locator

    security.declarePrivate('set_resourceLocator')
    def set_resourceLocator(self, force=False):
        """ """
        if not self.resource_locator:
            self.resource_locator = str(self.get_nextId())

    security.declarePublic('processForm')
    def processForm(self, form):
        """ Process an XForms submission.
        
        """
        submit = form.get('__submit__')
        if not submit:
            # return an empty string as the 'message', since we haven't actually
            # processed anything    
            return (form, '', False)
        
        model, submission = submit.split('+')
        if not (model and submission):
            return (form, 'No model and/or submission specified', True)
        
        messages = []
        # validate the form
        content_container = getattr(self.aq_explicit, self.content_container)
        for key in form.keys():
            for obj in (content_container.get_filteredDataDefinition() +
                        content_container.security_management):
                if (getattr(obj, 'indexName', '') == key or
                    getattr(obj, 'id', '') == key):
                    val, message = obj.validate(self, form.get(key))
                    if message:
                        messages.append(message)
                    else:
                        form[key] = val        
        if messages:
            message = ''
            for msg in messages:
                message += '<p>%s</p>' % msg
            
            return (form, message, True)
            
        # look for a callback method for processing this form
        if guarded_hasattr(self.aq_explicit, 'cb_'+str(model)):
            process_cb = guarded_getattr(self.aq_explicit, 'cb_'+str(model))
        
            # the form has been processed, we don't need to do anything else
            form['__populate__'] = False
            
            return process_cb(form)
            
        return (form, 'No matching model found', True)
        
# Zope Management Methods
#
manage_addXWFContentObjectForm = PageTemplateFile.PageTemplateFile(
    'management/manage_addXWFContentObjectForm.zpt',
    globals(), __name__='manage_addXWFContentObjectForm')

def manage_addXWFContentObject(self, id, file,
                               REQUEST=None, RESPONSE=None, submit=None):
    """ Add a new instance of XWFContentObject.
        
    """
    if not id and file:
        id = file.filename
    obj = XWFContentObject(id, file)
    self._setObject(id, obj)
    
    if RESPONSE and submit:
        if submit.strip().lower() == 'add':
            RESPONSE.redirect('%s/manage_main' % self.DestinationURL())
        else:
            RESPONSE.redirect('%s/manage_main' % id)

def initialize(context):
    context.registerClass(
        XWFContentObject,
        permission='Add XWF Content Object',
        constructors=(manage_addXWFContentObjectForm,
                      manage_addXWFContentObject),
        icon='icons/ic-xml.gif'
        )
