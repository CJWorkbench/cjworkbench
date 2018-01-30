// ---- Utilities ---
import * as Cookies from "js-cookie"
import timediff from 'timediff'

// return ID in URL of form "/workflows/id/" or "/workflows/id"
export function getPageID () {
  var url = window.location.pathname;

  // trim trailing slash if needed
  if (url.lastIndexOf('/' == url.length-1))
    url = url.substring(0, url.length-1);

  // take everything after last slash as the id
  var id = url.substring(url.lastIndexOf('/')+1);
  return id
};

export function goToUrl(url) {
  window.location.href = url;
}

// Current CSRF token
export const csrfToken = Cookies.get('csrftoken');

// Mocked server API object that does nothing, for tests where API never actually called
export class EmptyAPI {};
export var emptyAPI = new EmptyAPI();

// More testing fun
export function mockResponse (status, statusText, response) {
  return new window.Response(response, {
    status: status,
    statusText: statusText,
    headers: {
      'Content-type': 'application/json'
    }
  });
};

// Returns new mock function that returns given json. Used for mocking "get" API calls
export function jsonResponseMock (json) {
  return jest.fn().mockImplementation(()=>
    Promise.resolve(json)
  )
}

// Returns new mock function that gives an OK HTTP response. Use for mocking "set" API calls
export function okResponseMock () {
  return jsonResponseMock(null)
}


export function timeDifference (start, end) {
  var diff = timediff(start,end);

  if (diff.years > 0) {
    if (diff.years == 1) {
      return "1y ago";
    } else {
      return "" + diff.years + "y ago";
    }
  }
  else if (diff.days > 0) {
    if (diff.days == 1) {
      return "1d ago";
    } else {
      return "" + diff.days + "d ago";
    }
  }
  else if (diff.hours > 0) {
    if (diff.hours == 1) {
      return "1h ago";
    } else {
      return "" + diff.hours + "h ago";
    }
  }
  else if (diff.minutes > 0) {
    if (diff.minutes == 1) {
      return "1m ago";
    } else {
      return "" + diff.minutes + "m ago";
    }
  }
  else {
    return "now";
  }
}

// Log to Intercom, if installed
export function logUserEvent(name, metadata) {
  if (window.APP_ID) {
    window.Intercom("trackEvent", name, metadata);
  }
}
