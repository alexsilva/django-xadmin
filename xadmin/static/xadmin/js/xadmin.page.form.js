;(function($){
    $(function() {
        var action_bar = $('.form-actions');
        if (action_bar.length && !action_bar.data("action_scroll_top")) {
            var action_bar_height = action_bar.outerHeight(true);
            var $html = $('html');

            var onchange = function () {
                var html_height = $html.innerHeight();
                var html_scroll_top = $html.scrollTop();
                var html_scroll_height = $html.prop('scrollHeight');
                var action_bar_offset_top = action_bar.offset().top;

                var has_scroll_end = html_height + html_scroll_top >= html_scroll_height;
                var action_bar_coordenate = action_bar_offset_top + action_bar_height;
                var avaliable_action_bar_fixed = (html_scroll_top + html_height) < action_bar_coordenate;

                if (!action_bar.hasClass("fixed") && avaliable_action_bar_fixed) {
                    action_bar.addClass('fixed');

                } else if (has_scroll_end || avaliable_action_bar_fixed) {
                    action_bar.removeClass('fixed');
                }
            }
            action_bar.data("action_scroll_top", true);
            $(window).scroll(onchange);
            $(window).resize(onchange);
            $('a[data-toggle=tab]').on('shown.bs.tab', function (){
                action_bar.removeClass('fixed');
                onchange();
            });
            onchange();
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

