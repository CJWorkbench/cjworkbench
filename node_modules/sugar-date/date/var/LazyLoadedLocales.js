'use strict';

var BritishEnglishDefinition = require('./BritishEnglishDefinition'),
    AmericanEnglishDefinition = require('./AmericanEnglishDefinition'),
    CanadianEnglishDefinition = require('./CanadianEnglishDefinition');

var LazyLoadedLocales = {
  'en-US': AmericanEnglishDefinition,
  'en-GB': BritishEnglishDefinition,
  'en-AU': BritishEnglishDefinition,
  'en-CA': CanadianEnglishDefinition
};

module.exports = LazyLoadedLocales;