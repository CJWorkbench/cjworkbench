// ---- Utilities ---
import * as Cookies from "js-cookie"

export function goToUrl(url) {
  window.location.href = url;
}

// Current CSRF token
export const csrfToken = Cookies.get('csrftoken');

// Mocked server API object that does nothing, for tests where API never actually called
export class EmptyAPI {}
export var emptyAPI = new EmptyAPI();


// Find if an module of moduleIdName exists as or is next to module with wfModuleId
export function findModuleWithIdAndIdName(state, wfModuleId, moduleIdName) {
  var wfModules = state.workflow.wf_modules;
  var idx = getWfModuleIndexfromId(state, wfModuleId);

  // Is this an existing module with the wfModuleId we want?
  if (wfModules[idx].module_version.module.id_name === moduleIdName ) {
    return wfModules[idx];
  }

  // Is the next module one with moduleIdName? If so we will return this module to change
  var nextIdx = idx + 1;
  if (nextIdx === wfModules.length) {
    return null;   // end of stack
  } else if (wfModules[nextIdx].module_version.module.id_name === moduleIdName ) {
    return wfModules[nextIdx];
  }

  // Nope, no target module with moduleIdName where we need it
  return null;
}

// Find the parameter value by its id name
export function findParamValByIdName(wfm, paramValIdName) {
  return wfm.parameter_vals.find((parameterVal) => {
        return parameterVal.parameter_spec.id_name === paramValIdName;
    });
}

// Returns wfm object index in stack,  given its global ID
export function getWfModuleIndexfromId(state, id) {
  var wfModuleIdx = null;
  state.workflow.wf_modules.find((wfm, idx) => {
    wfModuleIdx = idx;
    return wfm.id === id;
  });

  return wfModuleIdx;
}

// Log to Intercom, if installed
export function logUserEvent(name, metadata) {
  if (window.APP_ID) {
    window.Intercom("trackEvent", name, metadata);
  }
}

export function timeDifference (start, end) {
  const ms = new Date(end) - new Date(start)
  const minutes = Math.floor(ms / 1000 / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const years = Math.floor(days / 365.25)

  if (years > 0) {
    if (years == 1) {
      return "1y ago";
    } else {
      return "" + years + "y ago";
    }
  }
  else if (days > 0) {
    if (days == 1) {
      return "1d ago";
    } else {
      return "" + days + "d ago";
    }
  }
  else if (hours > 0) {
    if (hours == 1) {
      return "1h ago";
    } else {
      return "" + hours + "h ago";
    }
  }
  else if (minutes > 0) {
    if (minutes == 1) {
      return "1m ago";
    } else {
      return "" + minutes + "m ago";
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

export function nonce(prefix) {
  let text = "";
  let possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for(let i = 0; i < 20; i++) {
      text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return prefix + text;
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
