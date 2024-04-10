var gulp = require('gulp'),
    node_modules = "node_modules";

function genericTask() {
    var srcs = [
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor'));
}

function jqueryTask() {
    return gulp.src(`${node_modules}/jquery/dist/**`)
        .pipe(gulp.dest('vendor/jquery'));
}

function nunjunksTask() {
    return gulp.src(`${node_modules}/nunjucks/browser/*.js`)
        .pipe(gulp.dest('vendor/nunjucks'));
}


function flotTask() {
    return gulp.src(`${node_modules}/flot/source/*.js`)
        .pipe(gulp.dest('vendor/flot/js'));

}

function micropluginTask() {
    return gulp.src(`${node_modules}/microplugin/src/*.js`)
        .pipe(gulp.dest('vendor/microplugin/js'));

}

function sifterTask() {
    return gulp.src(`${node_modules}/sifter/*.js`)
        .pipe(gulp.dest('vendor/sifter/js'));
}

function selectizeTask() {
    return gulp.src([
        "bower_components/selectize/dist/**/*.js",
        "bower_components/selectize/dist/**/*.css",
        "!bower_components/selectize/dist/lib/**"])
        .pipe(gulp.dest('vendor/selectize'));
}

function select2Task() {
    return gulp.src([`${node_modules}/select2/dist/**/*.js`,
                     `${node_modules}/select2/dist/**/*.css`,
                     `${node_modules}/select2/dist/**/i18n/*.js`,
                     `!${node_modules}/select2/dist/**/select2.full*`])
        .pipe(gulp.dest('vendor/select2'));
}

function datejsTask() {
    return gulp.src(`${node_modules}/datejs/src/**`)
        .pipe(gulp.dest('vendor/datejs/js'));
}

function popperjsTask() {
    return gulp.src(`${node_modules}/popper.js/dist/umd/**`)
        .pipe(gulp.dest('vendor/popper'));
}

function jqueryUITask() {
    var srcs = [
        `${node_modules}/jquery-ui/**/core.js`,
        `${node_modules}/jquery-ui/**/effect.js`,
        `${node_modules}/jquery-ui/**/widget.js`,
        `${node_modules}/jquery-ui/**/**/mouse.js`
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/jquery-ui'));
}

function html5SortableTask() {
    var srcs = [
        `${node_modules}/html5sortable/dist/html5sortable.js`,
        `${node_modules}/html5sortable/dist/html5sortable.min.js`
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/html5sortable'));
}

function fontAwesomeTask() {
    var srcs = [
        "bower_components/font-awesome/**/*.js",
        "bower_components/font-awesome/**/*.css",
        "bower_components/font-awesome/**/otfs/**",
        "bower_components/font-awesome/**/webfonts/**",
        "!bower_components/font-awesome/js-packages/**",
        "!bower_components/font-awesome/**/README.md",
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/font-awesome'));
}

function bootstrapTask() {
    var srcs = [
        `${node_modules}/bootstrap/dist/**/*.css`,
        `${node_modules}/bootstrap/dist/**/*.js`
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/bootstrap'));
}

exports.select2 = select2Task;
exports.selectize = selectizeTask;
exports.jquery = jqueryTask;
exports.nunjunks = nunjunksTask;
exports.default = gulp.series(
    //genericTask,
    jqueryTask,
    popperjsTask,
    nunjunksTask,
    flotTask,
    //sifterTask,
    //micropluginTask,
    fontAwesomeTask,
    selectizeTask,
    select2Task,
    datejsTask,
    jqueryUITask,
    html5SortableTask,
    bootstrapTask
);
