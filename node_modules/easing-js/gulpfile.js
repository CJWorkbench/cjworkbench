'use strict';
process.env.NODE_ENV = process.env.NODE_ENV || 'development';

require('babel/register')({experimental: true});
var requireDir = require('require-dir');
requireDir('./tasks');