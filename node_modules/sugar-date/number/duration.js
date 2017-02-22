'use strict';

var Sugar = require('sugar-core'),
    LocaleHelpers = require('../date/var/LocaleHelpers');

var localeManager = LocaleHelpers.localeManager;

Sugar.Number.defineInstance({

  'duration': function(n, localeCode) {
    return localeManager.get(localeCode).getDuration(n);
  }

});

module.exports = Sugar.Number.duration;