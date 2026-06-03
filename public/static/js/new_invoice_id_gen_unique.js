// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field
function populateNewInvoiceIdGenerate() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of new_code_airline input field
            document.querySelector('input[name="for_account_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdGenerate();
});



// start handleRenderSelectPickerUpdateCustomer
var handleRenderSelectPickerUpdateCustomer = function(selectId) {
    $('#' + selectId).picker({ search: true });
};

/* Controller */
$(document).ready(function() {
    {% for account in account_data_retrieve %}
    handleRenderSelectPickerUpdateCustomer('update-customer-ex-search-{{ account.account_id }}');
    {% endfor %}
});
// end handleRenderSelectPickerUpdateCustomer