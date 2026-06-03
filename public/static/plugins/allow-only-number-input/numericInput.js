/**
 * numericInput-js
 * https://github.com/nanachi-code/numericInput-js
 *
 * Force input fields to accept numeric value only.
 *
 * @version 1.0.1
 * @author Nanachi <github.com/nanachi-code>
 */
(function ($) {
    $.fn.numericInput = function (options) {
        options = $.extend(
            {},
            {
                maxDigits: null,
            },
            options
        );

        // Set attribute
        if (this.attr("numericinput") != undefined) {
            throw new Error("Call on an already initialized input!");
        } else {
            this.attr("numericinput", "");
            if (options.maxDigits) {
                this.attr("maxdigits", options.maxDigits);
            }
        }
        return this;
    };

    $(function () {
        $(document).on("input", "[numericinput]", function () {
            let max = $(this).attr("maxdigits");
            let _val =
                max != undefined
                    ? $(this).val().replace(/\D/g, "").substring(0, max)
                    : $(this).val().replace(/\D/g, "");
            // Update value
            $(this).val(_val);
        });
    });
})(jQuery);
