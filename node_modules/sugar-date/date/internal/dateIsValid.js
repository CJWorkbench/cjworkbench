'use strict';

function dateIsValid(d) {
  return !isNaN(d.getTime());
}

module.exports = dateIsValid;