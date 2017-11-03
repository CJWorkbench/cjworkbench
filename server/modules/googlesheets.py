from .moduleimpl import ModuleImpl
from .utils import *
from cjworkbench.google_oauth import maybe_authorize
from django.http import JsonResponse, HttpResponseBadRequest
import httplib2
from googleapiclient.discovery import build
from .utils import *
import io

class GoogleSheets(ModuleImpl):

    @staticmethod
    def get_spreadsheets(request):
        authorized, credential = maybe_authorize(request)

        if not authorized:
            return JsonResponse({'login_url':credential}, status=401)

        http = httplib2.Http()
        http = credential.authorize(http)
        service = build("drive", "v3", http=http)

        files_request = service.files().list(q="mimeType = 'application/vnd.google-apps.spreadsheet'", pageSize=1000)
        files = files_request.execute()
        return JsonResponse(files)

    @staticmethod
    def get_spreadsheet(request, id):
        authorized, credential = maybe_authorize(request)

        if not authorized:
            return credential

        http = httplib2.Http()
        http = credential.authorize(http)
        service = build("drive", "v2", http=http)

        files_request = service.files().export(fileId=id, mimeType="text/csv")
        the_file = files_request.execute()
        return the_file.decode("utf-8")
        #return JsonResponse({'file':the_file.decode("utf-8")})

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        tablestr = wf_module.retrieve_data()
        if (tablestr != None) and (len(tablestr) > 0):
            return pd.read_csv(io.StringIO(tablestr))
        else:
            return None

    @staticmethod
    def event(wfmodule, parameter, event, request = None):
        if not request:
            return HttpResponseBadRequest

        sheet_id = request.data.get('id', False)

        if sheet_id:
            new_data = GoogleSheets.get_spreadsheet(request, sheet_id)
            save_data_if_changed(wfmodule, new_data, auto_change_version=True)
            return JsonResponse({}, status=204)

        return GoogleSheets.get_spreadsheets(request)
