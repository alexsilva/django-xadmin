jQuery(function($){
    //full screen btn
    $('.layout-btns .layout-full').click(function(e){
        var icon = $(this).find('i');
        if($(this).hasClass('active')){
            // reset
            $('#left-side, ul.breadcrumb').show('fast');
            $('#content-block')
                .removeClass('col-sm-12 col-md-12 col-xl-12 ml-0 full-content')
                .addClass('col-md-10 col-lg-8 col-xl-9');
            icon.removeClass('fa-compress').addClass('fa-expand');
            $(window).trigger('resize');
        } else {
            // full screen
            $('#left-side, ul.breadcrumb').hide('fast', function(){
                $('#content-block')
                    .removeClass('col-md-10 col-lg-8 col-xl-9')
                    .addClass('col-sm-12 col-md-12 col-xl-12 ml-0 full-content');
                icon.removeClass('fa-expand').addClass('fa-compress');
                $(window).trigger('resize');
            });
        }
    });

    $('.layout-btns .layout-normal').click(function(e){
        $('.results table').removeClass('table-sm');
    });

    $('.layout-btns .layout-condensed').click(function(e){
        $('.results table').addClass('table-sm');
    });

});