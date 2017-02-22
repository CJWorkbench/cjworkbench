'use strict'

var hasOwn = Object.prototype.hasOwnProperty

function curry(fn, n){

    if (typeof n !== 'number'){
        n = fn.length
    }

    function getCurryClosure(prevArgs){

        function curryClosure() {

            var len  = arguments.length
            var args = [].concat(prevArgs)

            if (len){
                args.push.apply(args, arguments)
            }

            if (args.length < n){
                return getCurryClosure(args)
            }

            return fn.apply(this, args)
        }

        return curryClosure
    }

    return getCurryClosure([])
}


module.exports = curry(function(object, property){
    return hasOwn.call(object, property)
})