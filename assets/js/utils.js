// ---- Utilities ---
import * as Cookies from "js-cookie";


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