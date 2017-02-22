'use strict';

var Sugar = require('sugar-core'),
    LocaleHelpers = require('./var/LocaleHelpers'),
    getKeys = require('../common/internal/getKeys');

var localeManager = LocaleHelpers.localeManager;

Sugar.Date.defineStatic({

  'getAllLocaleCodes': function() {
    return getKeys(localeManager.getAll());
  }

});

module.exports = Sugar.Date.getAllLocaleCodes;