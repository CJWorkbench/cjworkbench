import io
import json
import os
from urllib.parse import urlsplit
import requests
import pandas as pd
from django.core.exceptions import ValidationError
from django.forms import URLField
from server.versions import save_fetched_table_if_changed

def handle_dotcom_url(wf_module, url, split_url, num_rows):
    """
    Constructs the URL we'll use to query Enigma if the user passes in a URL to the publicly
    browsable page as opposed to enigma.io.
    Returns the Pandas table if everything goes off smoothly.
    Else, throws an error.
    """
    if not "ENIGMA_COM_API_KEY" in os.environ:
        return("No Enigma API Key set.")

    api_key = os.environ["ENIGMA_COM_API_KEY"]

    try:
        dataset_id = split_url.path.split('/')[3]
    except Exception as e:
        return("Unable to retrieve the dataset id from request.")

    request_url = "https://public.enigma.com/api/datasets/{}?row_limit={}".format(dataset_id, num_rows)
    headers = {
        "authorization": "Bearer " + api_key
    }
    response = requests.get(request_url, headers=headers)
    if response.status_code == 200:
        resultset = json.loads(response.text)
        # first retrieve the headers (i.e. the column names)
        column_headers = resultset["current_snapshot"]["table_rows"]["fields"]

        #now extract the actual data
        data = resultset["current_snapshot"]["table_rows"]["rows"]

        #...and finally create the Pandas object to return.
        table = pd.DataFrame(data, columns=column_headers)
        return table
    else:
        error = json.loads(response.text)
        if "message" in error:
            return("Received error \"{}\" whilst retrieving data from {}".format(error["message"], url))
        else: # this should hopefully never get hit, but let's err on the side of caution.
            return("Received error status {} whilst retrieving data from {}}".format(response.status_code, url))

def handle_dotio_url(wf_module, url, split_url, num_rows):
    """
    Processes response for any request to enigma.io. Here, we assume that the API key is provided,
    because, at least at first glance (or two or three) there doesn't seem to be any provisions for
    accessing dataset endpoints sans API key.
    """

    if num_rows > 500:
        return("You can request a maximum of 500 rows.")

    if "/limit/" not in url:
        if url.endswith('/'):
            url += "limit/{}".format(num_rows)
        else:
            url += "/limit/{}".format(num_rows)

    response = requests.get(url)
    if response.status_code != 200:
        error = json.loads(response.text)
        if "message" in error:
            message = error["message"]
        else:
            message = error["info"]["message"]
            if "additional" in error["info"]:
               message += ": " + error["info"]["additional"]["message"]
        return("Unable to retrieve data from Enigma. Received {} status, with message {}"
            .format(response.status_code, message))
    try:
        json_text = json.loads(response.text)
        table = pd.read_json(json.dumps(json_text['result']))
        return table
    except Exception as ex: # Generic exceptions suck, but is it the most pragmatic/all-encompassing here?
        return("Unable to process request: {}".format(str(ex)))

class EnigmaDataLoader:
    @staticmethod
    def __init__():
        pass

    @staticmethod
    def event(wf_module, **kwargs):
        #number of rows we want to retrieve from Enigma. If you leave this blank/let it use the default,
        #you get all of 0 rows, so it should have a value > 0.
        wf_module.set_busy(notify=False)
        try:
            num_rows = int(wf_module.get_param_string("num_rows"))
        except ValueError:
            wf_module.set_error("The number of rows specified must be an integer, but it's {}."
                .format(wf_module.get_param_string("num_rows")))
            return None

        # We can get one of two _types_ of Enigma URLs here:
        # - any URL with the .com TLD indicates that the URL is publicly browsable, and so we'll extract
        # the name of the dataset, construct the URL, and make a call using our API key.
        # - any URL with the .io TLD indicates that the URL is probably already using the API, so we we can$
        # simply send off the request to Enigma.
        url = wf_module.get_param_string('enigma_url')

        url_form_field = URLField()
        try:
            url = url_form_field.clean(url)
        except ValidationError:
            wf_module.set_error('Invalid URL entered: {}'.format((url)))
            return

        #let's break the url down to its components
        split_url = urlsplit(url)
        netloc = split_url.netloc

        # quick basic validation: ensure it's an Enigma URL$
        if netloc.split(".")[1].lower() != 'enigma':
            wf_module.set_error("The URL entered, {}, is not an Enigma URL.".format(netloc))
            return None  # there's no point going any further for obvious reasons

        # quick basic validation: ensure the TLD is .com or .io.
        if netloc.split(".")[2].lower() not in ["com", "io"]:
            wf_module.set_error("The top-level domain specified has to be .com or .io, but " +
                " the top-level domain in the URL received is {}.".format(netloc.split(".")[2]))
            return None # there's no point going any further for obvious reasons

        # Can wrap this around a single try because only one or the other will be called.
        try:
            if netloc.endswith("io"):
                data = handle_dotio_url(wf_module, url, split_url, num_rows)

            else:
                # this has to be ".com" as we've already done the check above for dodgy URLs.
                # this returns the Pandas table.
                data = handle_dotcom_url(wf_module, url, split_url, num_rows)
        except Exception as ex:
            wf_module.set_error("Caught error whilst attempting to retrieve details from Enigma: {}".format(str(ex)))

        # If we have got this far, and not run into any issues, we should do some data versioning magic.
        if wf_module.status != wf_module.ERROR:
            wf_module.set_ready(notify=False)
            csv_data = data.to_csv(index=False)
            updated = wf_module.auto_update_data or event.get('type') == 'click'

            save_fetched_table_if_changed(wf_module, csv_data, auto_change_version=updated)

    @staticmethod
    def render(wf_module, table):
        """
        Propagates the table to the front-end.
        Here, event() does all the heavy lifting.
        """
        retrieved_data = wf_module.retrieve_data()
        if retrieved_data != None and len(retrieved_data):
            return pd.read_csv(io.StringIO(retrieved_data))
        else:
            return None
