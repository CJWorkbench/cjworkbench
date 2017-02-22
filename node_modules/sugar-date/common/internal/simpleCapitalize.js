'use strict';

function simpleCapitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

module.exports = simpleCapitalize;