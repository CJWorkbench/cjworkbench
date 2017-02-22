'use strict';

var CoreOutputFormats = require('../var/CoreOutputFormats'),
    formattingTokens = require('../var/formattingTokens'),
    assertDateIsValid = require('./assertDateIsValid');

var dateFormatMatcher = formattingTokens.dateFormatMatcher;

function dateFormat(d, format, localeCode) {
  assertDateIsValid(d);
  format = CoreOutputFormats[format] || format || '{long}';
  return dateFormatMatcher(format, d, localeCode);
}

module.exports = dateFormat;