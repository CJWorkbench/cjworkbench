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



// Log to Intercom, if installed
export function logUserEvent(name, metadata) {
  if (window.APP_ID) {
    window.Intercom("trackEvent", name, metadata);
  }
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

export function escapeHtml(str) {
  str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

  return str;
}

export function scrollTo(scrollTo, scrollDuration, scroller, offset) {

// Smooth scroll-to inspired by:
// https://gist.github.com/joshcanhelp/a3a669df80898d4097a1e2c01dea52c1
  let scrollToObj;

  if (typeof scroller === 'undefined') {
	  scroller = window;
  }

	if (scrollTo && typeof scrollTo.getBoundingClientRect === 'function') {

		// Assuming this is a selector we can use to find an element
		scrollToObj = scrollTo;
		scrollTo = (scroller.scrollTop + (scrollToObj.getBoundingClientRect().y - scroller.getBoundingClientRect().y));

	} else if (typeof scrollTo !== 'number') {

		// If it's nothing above and not an integer, we assume top of the window
		scrollTo = 0;
	}

	// Set this a bit higher

	var anchorHeightAdjust = offset || 0;

  scrollTo = scrollTo - anchorHeightAdjust;

	//
	// Set a default for the duration
	//

	if ( typeof scrollDuration !== 'number' || scrollDuration < 0 ) {
		scrollDuration = 1000;
	}

	var cosParameter = (scroller.scrollTop - scrollTo) / 2,
		scrollCount = 0,
		oldTimestamp = window.performance.now();

	function step(newTimestamp) {

		var tsDiff = newTimestamp - oldTimestamp;

		// Performance.now() polyfill loads late so passed-in timestamp is a larger offset
		// on the first go-through than we want so I'm adjusting the difference down here.
		// Regardless, we would rather have a slightly slower animation than a big jump so a good
		// safeguard, even if we're not using the polyfill.

		if (tsDiff > 100) {
			tsDiff = 30;
		}

		scrollCount += Math.PI / (scrollDuration / tsDiff);

		// As soon as we cross over Pi, we're about where we need to be

		if (scrollCount >= Math.PI) {
			return;
		}

		var moveStep = Math.round(scrollTo + cosParameter + cosParameter * Math.cos(scrollCount));
		scroller.scrollTo(0, moveStep);
		oldTimestamp = newTimestamp;
		window.requestAnimationFrame(step);
	}

	window.requestAnimationFrame(step);

}

//
// Performance.now() polyfill from:
// https://gist.github.com/paulirish/5438650
//

(function () {

	if ("performance" in window == false) {
		window.performance = {};
	}

	Date.now = (Date.now || function () {  // thanks IE8
		return new Date().getTime();
	});

	if ("now" in window.performance == false) {

		var nowOffset = Date.now();

		if (performance.timing && performance.timing.navigationStart) {
			nowOffset = performance.timing.navigationStart
		}

		window.performance.now = function now() {
			return Date.now() - nowOffset;
		}
	}

})();