'use strict';

var LocaleHelpers = require('../var/LocaleHelpers'),
    trunc = require('../../common/var/trunc'),
    getHours = require('./getHours');

var localeManager = LocaleHelpers.localeManager;

function getMeridiemToken(d, localeCode) {
  var hours = getHours(d);
  return localeManager.get(localeCode).ampm[trunc(hours / 12)] || '';
}

module.exports = getMeridiemToken;