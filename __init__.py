# Copyright IOPEN Technologies Ltd., 2003
# richard@iopen.net
#
# For details of the license, please see LICENSE.
#
# You MUST follow the rules in http://iopen.net/STYLE before checking in code
# to the head. Code which does not follow the rules will be rejected.  
#

import sys, traceback
def log(err):
    sys.stderr.write('DataTemplates: %s\n' % err)
    traceback.print_exc(sys.stderr)

def initialize(context):
    # Import lazily, and defer initialization to the module
    import XWFContentObject
    XWFContentObject.initialize(context)
