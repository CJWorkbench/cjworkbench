'use strict';

var Sugar = require('sugar-core'),
    LocaleHelpers = require('./var/LocaleHelpers');

var localeManager = LocaleHelpers.localeManager;

Sugar.Date.defineStatic({

  'getAllLocales': function() {
    return localeManager.getAll();
  }

});

module.exports = Sugar.Date.getAllLocales;