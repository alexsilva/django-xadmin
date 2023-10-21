(function($) {
  $(function(){
    if($("#g-theme-menu")){
      $('#g-theme-menu a').click(function(evt){
        evt.preventDefault();
        var $el = $(this);
        var themeHref = $el.data('css-href');
        
        var topmenu = $('#top-nav .navbar-collapse');
        if(topmenu.data('bs.collapse')) topmenu.collapse('hide');

        var modal = xadmin.bs_modal({
            header: {title: gettext('Loading theme')},
            modal: {id: 'load-theme-modal', size: 'modal-md',},
            footer: '&nbsp'
          });
        modal.loading();
        modal.appendTo('body');
        modal.$el().on('shown.bs.modal', function(){
          $.save_user_settings("site-theme", themeHref, function(){
            $.setCookie('_theme', themeHref);

            var $iframe = $("<iframe>");
            $iframe.addClass("d-none");
            $iframe.appendTo(document.body);

            modal.$el().on('hidden.bs.modal', function() {
              modal.$el().remove();
            });

            $iframe.on("load", function () {
              $('#site-theme').attr('href', themeHref);
              modal.hide();
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
        modal.show();
      })
    }
  });

})(jQuery);