(function($) {
  $(function(){
    if($("#g-theme-menu")){
      $('#g-theme-menu a').click(function(evt){
        evt.preventDefault();
        var $el = $(this);
        var themeHref = $el.data('css-href');
        
        var topmenu = $('#top-nav .navbar-collapse');
        if(topmenu.data('bs.collapse')) topmenu.collapse('hide');

        var modal = $("#nunjucks-modal-main").template_render$({
            header: {title: gettext('Loading theme')},
            modal: {id: 'load-theme-modal', size: 'modal-md',},
            body: '<h2 class="text-center"><i class="fa-spinner fa-spin fa fa-large"></i></h2>',
            footer: '&nbsp'
          }).appendTo('body');

        modal.on('shown.bs.modal', function(){
          $.save_user_settings("site-theme", themeHref, function(){
            $.setCookie('_theme', themeHref);

            var $iframe = $("<iframe>");
            $iframe.addClass("d-none");
            $iframe.appendTo(document.body);

            modal.on('hidden', function() {
              modal.remove();
            });

            $iframe.on("load", function () {
              $('#site-theme').attr('href', themeHref);

              modal.modal('hide');
              $iframe.remove();
            });

            $iframe.attr('src', window.location.href);
            $iframe.append('<!doctype><html><head></head><body>');
            $iframe.append('<link rel="stylesheet" href="'+themeHref+'" />');
            $iframe.append('</body></html>');

            // option selected
            $el.parent().find("a").removeClass('active');
            $el.addClass('active');
          });
        });

        modal.modal().css(
            {
                'margin-top': function () {
                    return window.pageYOffset;
                }
            });
      })
    }
  });

})(jQuery);