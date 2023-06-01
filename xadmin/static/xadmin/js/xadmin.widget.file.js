(function ($) {
  /**
   * jQuery plugin that adds behavior to file input elements.
   * This plugin updates the label text based on the selected files.
   */
  $.fn.fileInputBehavior = function () {
    return this.each(function () {
      var $fileInput = $(this).addClass('behavior');
      var $fileLabel = $fileInput.next('.custom-file-label');
      var originalLabel = $fileLabel.text();

      $fileLabel.data('label', originalLabel);

      $fileInput.on('change', function () {
        var files = this.files,
            numFiles = files.length;

        $fileLabel.text(numFiles + ' files selected');

        if (numFiles <= 2) {
          var index, fileNames = [];

          for (index = 0; index < numFiles; index++) {
            fileNames.push(files[index].name);
          }

          $fileLabel.text(fileNames.join(', '));
        }

        if (numFiles === 0) {
          $fileLabel.text(originalLabel);
        }
      });
    });
  };
})(jQuery);


$(function () {
  $('.custom-file > .custom-file-input:not(.behavior)').fileInputBehavior();
})