'use strict';

var express = require('express')
var app     = express()
var gen     = require('./gen')

app.use(function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
  next();
});

var paginate = (function(){
	var cache = {}

	return function(size){
		var data = cache[size] = cache[size] || gen(size)

		return function(config){
			if (isNaN(config.skip)){
				return data
			}

			return data.slice(config.skip, config.skip + (config.pageSize || 20))
		}
	}
})()

function page(size, timeout){
	return function(req, res){
		var json = paginate(size)({
				pageSize: req.query.pageSize * 1,
				skip    : req.query.skip * 1
			})

		setTimeout(function(){
			res.send({
				data : json,
				count: size
			})
		}, timeout || 0)

	}
}

app.get('/', function (req, res) {
  	res.send('Hello World!')
})

var timeout = 300
app.get('/50000', page(50000, timeout))
app.get('/20000', page(20000, timeout))
app.get('/10000', page(10000, timeout))

app.get('/5000', page(5000, timeout))
app.get('/2000', page(2000, timeout))
app.get('/1000', page(1000, timeout))

app.get('/500', page(500, timeout))
app.get('/200', page(200, timeout))
app.get('/100', page(100, timeout))

app.get('/10', page(10, timeout))

var server = app.listen(3000, function () {

	var host = server.address().address
  	var port = server.address().port

  	console.log('Example app listening at http://%s:%s', host, port)
})