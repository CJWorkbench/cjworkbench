'use strict';

var gulp  = require('gulp')
var babel = require('gulp-babel')

var SRC = './src/**'

gulp.task('lib', function () {
    return gulp.src(SRC)
        .pipe(babel())
        .pipe(gulp.dest('./lib'))
});

gulp.task('w', function(){
	gulp.watch(SRC, ['lib'])
})

gulp.task('watch',['lib','w'])
gulp.task('default',['lib'])