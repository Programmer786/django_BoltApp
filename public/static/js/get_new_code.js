// Function to fetch the maximum account_id from the server and set it as the value of new_code_account input field
function populateNewCodeAccount() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_account_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of new_code_account input field
            document.querySelector('input[name="new_code_account"]').value = data.max_account_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewCodeAccount();
});


// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field for_account_balance_invoice_no
function populateNewInvoiceIdAccountGenerate() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of for_account_balance_invoice_no input field
            document.querySelector('input[name="for_account_balance_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdAccountGenerate();
});


// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field cash_received_invoice_no
function populateNewInvoiceIdGenerateReceived() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of cash_received_invoice_no input field
            document.querySelector('input[name="cash_received_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdGenerateReceived();
});


// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field cash_payment_invoice_no
function populateNewInvoiceIdGeneratePayment() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of cash_payment_invoice_no input field
            document.querySelector('input[name="cash_payment_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdGeneratePayment();
});


// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field bank_deposit_invoice_no
function populateNewInvoiceIdGenerateBankDeposit() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of bank_deposit_invoice_no input field
            document.querySelector('input[name="bank_deposit_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdGenerateBankDeposit();
});

// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field bank_payment_invoice_no
function populateNewInvoiceIdGenerateBankPayment() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of bank_payment_invoice_no input field
            document.querySelector('input[name="bank_payment_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdGenerateBankPayment();
});


// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field journal_voucher_invoice_no
function populateNewInvoiceIdGenerateJournalVoucher() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of journal_voucher_invoice_no input field
            document.querySelector('input[name="journal_voucher_invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewInvoiceIdGenerateJournalVoucher();
});



