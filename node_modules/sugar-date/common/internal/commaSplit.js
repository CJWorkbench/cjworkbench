'use strict';

var CommonChars = require('../var/CommonChars');

var HALF_WIDTH_COMMA = CommonChars.HALF_WIDTH_COMMA;

function commaSplit(str) {
  return str.split(HALF_WIDTH_COMMA);
}

module.exports = commaSplit;