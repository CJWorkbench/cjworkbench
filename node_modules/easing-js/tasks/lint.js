var gulp = require('gulp');
var plugins = require('gulp-load-plugins')();

gulp.task('lint', function () {
  return gulp.src(['gulpfile.js', 'src/**/*.js'])
    .pipe(plugins.eslint())
    .pipe(plugins.eslint.format('stylish'))
    .pipe(plugins.eslint.failOnError())
});