'use strict';

var Sugar = require('sugar-core'),
    LocaleHelpers = require('./var/LocaleHelpers');

var localeManager = LocaleHelpers.localeManager;

Sugar.Date.defineStatic({

  'removeLocale': function(code) {
    return localeManager.remove(code);
  }

});

module.exports = Sugar.Date.removeLocale;