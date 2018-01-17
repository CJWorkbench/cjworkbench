import os
import json
import re
from server.modules.moduleimpl import ModuleImpl
from django.http import HttpResponse
from server.serializers import WfModuleSerializer

# ---- Chart ----
class Chart(ModuleImpl):
    @staticmethod
    def output(wf_module, request=None, data=None):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        htmlfile = open(os.path.join(__location__, 'chart.html'), 'r+')
        htmlstr = htmlfile.read()
        serializer = WfModuleSerializer(wf_module)

        initData = json.dumps({
            'wfmodule':serializer.data,
            'input_data':json.loads(data) #I hate this
        })

        js_string="""
        <script>
        workbench = {
            data:%s
        }
        </script>""" % initData

        head_tag = re.compile('<\w*[H|h][E|e][A|a][D|d]\w*>')
        result = head_tag.search(htmlstr)

        #lordt forgive me
        glitter_turkey = '%s %s %s' % (
            htmlstr[:result.end()],
            js_string,
            htmlstr[result.end():]
        )

        return HttpResponse(content=glitter_turkey)
