;(function($){
    $(function() {
        var action_bar = $('.form-actions');
        if (action_bar.length && !action_bar.data("action_scroll_top")) {
            action_bar.data("action_scroll_top", true);
            var action_bar_offset = action_bar.offset().top;

             function isScrollAtEnd(marge) {
                var $window = $(window),
                    scroll_top = $window.scrollTop(),
                    window_height = $window.height(),
                    pos = action_bar_offset - (scroll_top + window_height);
                return pos < marge;
            }

            var onchange = function (evt) {
                if (isScrollAtEnd(($(window).height() * 0.25))) {
                    action_bar.removeClass('fixed');
                } else if (!action_bar.hasClass("fixed")) {
                    action_bar.addClass('fixed');
                }
            }
            $(window).on("scroll", onchange)
                .on("resize", onchange)
                .trigger('scroll');
            $('a[data-toggle=tab]').on('shown.bs.tab', function (){
                action_bar.removeClass('fixed');
                onchange();
            });
        }
        if(window.xadmin.ismobile){
            $(window).bind('resize', function(e){
                var rate = $(window).height() / $(window).width();
                var action_bar = $('.form-actions');
                if(rate < 1){
                    action_bar.css('display', 'none');
                } else {
                    action_bar.css('display', 'block');
                }
            });
        }
    });
    var exform = $('.exform').first();
    if (exform.find('.invalid-feedback').length > 0){
        var first_activated = false;
        exform.find('.is-invalid').each(function(){
            if (!first_activated){
                var parent = $(this);
                while (parent.html() !== exform.html()){
                    if (parent.hasClass('tab-pane') || parent.hasClass('collapse')){
                        var $el = $('a[href="#' + parent.attr('id') + '"]');
                        if ($el.length === 0) {
                            $el = $('[data-target="#' + parent.attr('id') + '"]');
                        }
                        if (parent.hasClass('tab-pane')) {
                            $el.tab('show');
                        } else {
                            $el.collapse('show');
                        }
                        first_activated = true;
                    }
                    parent = parent.parent();
                }
            }
        });
    }
})(jQuery)

