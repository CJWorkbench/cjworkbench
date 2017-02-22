'use strict';

var chr = require('../../common/var/chr');

function incrementString(current, amount) {
  return chr(current.charCodeAt(0) + amount);
}

module.exports = incrementString;