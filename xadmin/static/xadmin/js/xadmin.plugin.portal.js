
$(function() {
    $(".column").html5sortable({
        acceptFrom: ".column",
        handle: '.card-header',
        hoverClass: "cursor-move",
        items: ":not(.unsort)",
        forcePlaceholderSize: true,
    }).each(function () {
        this.addEventListener('sortupdate',function( e ) {
            var pos = [];
            $('.column').each(function(){
                var col = [];
                $(this).find('.card').each(function(){
                    col.push($(this).attr('id'));
                });
                pos.push(col.join(','));
            });
            var pos_val = pos.join('|');
            var key = $('#_portal_key').val();
            $.save_user_settings(key, pos_val, function(){
                //alert('success');
            });
        });
    });
    $(".card-header .btn.btn-link" ).each(function () {
        var $el = $(this);
        if (!$el.data("chevron-up-down-click")) {
            $el.click(function() {
                $(this).find(".icon.chevron")
                    .toggleClass( "fa fa-chevron-up" )
                    .toggleClass( "fa fa-chevron-down" );
            });
            $el.data("chevron-up-down-click", true);
        }
    })
});
