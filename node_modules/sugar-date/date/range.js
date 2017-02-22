'use strict';

var Sugar = require('sugar-core'),
    DateRangeConstructor = require('../range/var/DateRangeConstructor');

Sugar.Date.defineStatic({

  'range': DateRangeConstructor

});

module.exports = Sugar.Date.range;