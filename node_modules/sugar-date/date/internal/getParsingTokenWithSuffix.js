'use strict';

var LocalizedParsingTokens = require('../var/LocalizedParsingTokens'),
    getRegNonCapturing = require('./getRegNonCapturing');

function getParsingTokenWithSuffix(field, src, suffix) {
  var token = LocalizedParsingTokens[field];
  if (token.requiresSuffix) {
    src = getRegNonCapturing(src + getRegNonCapturing(suffix));
  } else if (token.requiresSuffixOr) {
    src += getRegNonCapturing(token.requiresSuffixOr + '|' + suffix);
  } else {
    src += getRegNonCapturing(suffix, true);
  }
  return src;
}

module.exports = getParsingTokenWithSuffix;