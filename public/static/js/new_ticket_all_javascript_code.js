
// Function to fetch the maximum invoice_id from the server and set it as the value of invoice_no input field
function populateNewTicketCustomer() {
    // Make an AJAX request to fetch the maximum airline_id
    fetch('/get_max_invoice_id')
        .then(response => response.json())
        .then(data => {
            // Set the value of new_code_airline input field
            document.querySelector('input[name="invoice_no"]').value = data.max_invoice_id + 1;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewTicketCustomer();
});


// Start: This function will generate a other service number in the format "OTH-XXX-YYYYYY"
// Function to populate the new entry_ref number
function populateNewOtherServiceGenerate() {
    // Make an AJAX request to fetch the new entry_ref number
    fetch('/get_new_entry_ref_no')
        .then(response => response.json())
        .then(data => {
            // Set the value of entry_ref_no input field
            document.querySelector('input[name="entry_ref_no"]').value = data.new_entry_ref_no;
        })
        .catch(error => console.error('Error:', error));
}

// Call the function to populate the new entry_ref number when the page loads
document.addEventListener('DOMContentLoaded', function() {
    populateNewOtherServiceGenerate();
});
// End: This function will generate a other service number in the format "OTH-XXX-YYYYYY"



// this is use for handle formatting, masking, and validation of monetary input
$(":input").inputmask();
jQuery(function($){
    $("#invoice_date").mask("99/99/9999");
    $("#date-posting").mask("99/99/9999");
    $("#date-dep").mask("99/99/9999");
    $("#phone").mask("(9999) 9999999");
    $("#tin").mask("99-9999999");
    $("#ticket_no5").mask("999-9999-999999");
    $("#attach_last_ticket").mask("999-9999-999999");
});


// Start: specific format, such as "XXX-XXX-XXX-XXX-XXX-XXX-XXX-XXX AND SO ON"
document.getElementById('sector').addEventListener('input', function (e) {
    var value = e.target.value.replace(/[^a-zA-Z0-9\s-]/g, ''); // Allow space and hyphen characters
    var formattedValue = '';
    for (var i = 0; i < value.length; i++) {
        if (i > 0 && i % 3 === 0) {
            // Decide whether to include a space or hyphen, depending on your specific needs.
            // Remove the space between groups of three if not required.
            // Here we're not adding any extra characters.
        }
        formattedValue += value[i];
    }
    e.target.value = formattedValue;
});


// End: specific format, such as "XXX-XXX-XXX-XXX-XXX-XXX-XXX-XXX AND SO ON"


// Start: specific format, such as "XXX-XXXX-XXXXXX"
document.getElementById('ticket_no').addEventListener('input', function (e) {
    var value = e.target.value.replace(/[^a-zA-Z0-9]/g, ''); // Remove non-alphanumeric characters
    
    // Insert hyphens at specific positions
    var formattedValue = value.slice(0, 3) + '-' + value.slice(3, 7) + '-' + value.slice(7, 13);
    
    e.target.value = formattedValue;
});
// End: specific format, such as "XXX-XXXX-XXXXXX"


//Start: calculation all values inputs
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        input.addEventListener('input', calculateTaxes);
    });

    // GET FOR calculate comm_percent AND com_amt values
    const commPercentInput = document.getElementById('comm_percent');
    const comAmtInput = document.getElementById('com_amt');

    commPercentInput.addEventListener('input', calculateCommissionAmount);
    comAmtInput.addEventListener('input', calculateCommissionPercent);
    
    // GET FOR calculate psf_percent AND psf_amount values
    const psfPercentInput = document.getElementById('psf_percent');
    const psfAmountInput = document.getElementById('psf_amount');

    psfPercentInput.addEventListener('input', calculatePsfAmount);
    psfAmountInput.addEventListener('input', calculatePsfPercent);

    // GET FOR calculate disc_adj values
    const discAdjInput = document.getElementById('disc_adj');
    discAdjInput.addEventListener('input', calculateDiscAmount);
});

function calculateCommissionAmount() {
    const mkt_fare = parseFloat(document.getElementById('mkt_fare').value) || 0;
    const comm_percent = parseFloat(document.getElementById('comm_percent').value) || 0;
    const com_adj = parseFloat(document.getElementById('com_adj').value) || 0;
    const com_amt = mkt_fare * (comm_percent / 100);
    document.getElementById('com_amt').value = com_amt;

    // other section of commission
    const wh_air2 = com_amt * 0.12;
    document.getElementById('wh_air').value = wh_air2.toFixed(2);

    // tol_com AIRLINE of commission total
    const tol_com = com_amt + com_adj;
    document.getElementById('tol_com').value = tol_com.toFixed(2);

    calculateTaxes(); // Recalculate all values
}

function calculateCommissionPercent() {
    const mkt_fare = parseFloat(document.getElementById('mkt_fare').value) || 0;
    const com_amt = parseFloat(document.getElementById('com_amt').value) || 0;
    const com_adj = parseFloat(document.getElementById('com_adj').value) || 0;
    const comm_percent = (com_amt / mkt_fare) * 100;
    document.getElementById('comm_percent').value = comm_percent;

    // other section of commission
    const wh_air2 = com_amt * 0.12;
    document.getElementById('wh_air').value = wh_air2.toFixed(2);

    // tol_com AIRLINE of commission total
    const tol_com = com_amt + com_adj;
    document.getElementById('tol_com').value = tol_com.toFixed(2);

    calculateTaxes(); // Recalculate all values
}

function calculatePsfAmount() {
    const mkt_fare = parseFloat(document.getElementById('mkt_fare').value) || 0;
    const psf_percent = parseFloat(document.getElementById('psf_percent').value) || 0;
    const psf_amount = mkt_fare * (psf_percent / 100);
    document.getElementById('psf_amount').value = psf_amount;
    calculateTaxes(); // Recalculate all values
}

function calculatePsfPercent() {
    const mkt_fare = parseFloat(document.getElementById('mkt_fare').value) || 0;
    const psf_amount = parseFloat(document.getElementById('psf_amount').value) || 0;
    const psf_percent = (psf_amount / mkt_fare) * 100;
    document.getElementById('psf_percent').value = psf_percent;
    calculateTaxes(); // Recalculate all values
}

function calculateDiscAmount() {
    const disc_adj = parseFloat(document.getElementById('disc_adj').value) || 0;
    const receivable_client = parseFloat(document.getElementById('receivable_client').value) || 0;

    // Calculate disc_amount and update disc_amount input
    document.getElementById('disc_amount').value = disc_adj;
    calculateTaxes(); // Recalculate all values
    // Update receivable_client by subtracting disc_adj
    // const updatedReceivableClient = receivable_client - disc_adj;
    // document.getElementById('receivable_client').value = updatedReceivableClient;

    // // Recalculate profit_loss
    // const airline_payable = parseFloat(document.getElementById('airline_payable').value) || 0;
    // const profit_loss = updatedReceivableClient - airline_payable;
    // document.getElementById('profit_loss').value = profit_loss.toFixed(2);

}

function calculateTaxes() {
    const mkt_fare = parseFloat(document.getElementById('mkt_fare').value) || 0;
    const soto_fare = parseFloat(document.getElementById('soto_fare').value) || 0;
    const sp_yi = parseFloat(document.getElementById('sp_yi').value) || 0;
    const yd_sf_ftt = parseFloat(document.getElementById('yd_sf_ftt').value) || 0;
    const aq_yr_pk = parseFloat(document.getElementById('aq_yr_pk').value) || 0;
    const fed_rg_cvt = parseFloat(document.getElementById('fed_rg_cvt').value) || 0;
    const xz_jo = parseFloat(document.getElementById('xz_jo').value) || 0;
    const wh_air = parseFloat(document.getElementById('wh_air').value) || 0;
    const wh_client = parseFloat(document.getElementById('wh_client').value) || 0;
    const yq = parseFloat(document.getElementById('yq').value) || 0;
    const pb = parseFloat(document.getElementById('pb').value) || 0;
    const oth = parseFloat(document.getElementById('oth').value) || 0;
    const disc_adj = parseFloat(document.getElementById('disc_adj').value) || 0;

    // PSF (Passenger Service Fee) calculations
    const psf_percent = parseFloat(document.getElementById('psf_percent').value) || 0;
    const psf_amount = parseFloat(document.getElementById('psf_amount').value) || 0;

    // other section of commission
    const comm_percent = parseFloat(document.getElementById('comm_percent').value) || 0;
    const com_amt = mkt_fare * (comm_percent / 100);
    const wh_air2 = com_amt * 0.12;
    // total wh_air
    // document.getElementById('wh_air').value = wh_air2.toFixed(2);

    const com_adj = parseFloat(document.getElementById('com_adj').value) || 0;

    // total taxes including PSF
    const taxes = sp_yi + yd_sf_ftt + aq_yr_pk + fed_rg_cvt + xz_jo + wh_air + wh_client + yq + pb + oth;
    const fr_tx = mkt_fare + soto_fare + taxes;

    document.getElementById('taxes').value = taxes.toFixed(2);
    document.getElementById('fr_tx').value = fr_tx.toFixed(2);

    // airline_payable
    const tol_com = com_amt + com_adj;
    document.getElementById('tol_com').value = tol_com.toFixed(2);
    const airline_payable = fr_tx - tol_com;
    document.getElementById('airline_payable').value = airline_payable.toFixed(2);

    // receivable_client including PSF
    // const receivable_client = fr_tx - wh_air + psf_amount;

    // Update receivable_client by subtracting disc_adj
    const receivable_client = fr_tx - wh_air + psf_amount - disc_adj;
    document.getElementById('receivable_client').value = receivable_client.toFixed(2);



    // profit_loss including PSF
    const profit_loss = receivable_client - airline_payable;
    document.getElementById('profit_loss').value = profit_loss.toFixed(2);

    // ticket_value
    const ticket_value = fr_tx;
    document.getElementById('ticket_value').value = ticket_value.toFixed(2);
}

//End: ticket calculation


// remove the value="0" attribute from the input element" 
function removeDefaultValue(input) {
    if (input.value !== '0') {
        input.removeAttribute('value');
    }
}


// #Only ASCII character in that range allowed"
function onlyNumberKey(evt) {
    // Only ASCII character in that range allowed
    var ASCIICode = (evt.which) ? evt.which : evt.keyCode
    if (ASCIICode > 31 && (ASCIICode < 48 || ASCIICode > 57))
        return false;
    return true;
}


// Start: This function will generate a ticket number in the format "PNR-XXX-YYYYYY"
document.getElementById('modeSelect').addEventListener('change', function() {
    var ticketNoInput = document.getElementById('ticket_no');
    var selectedMode = this.value;
    
    if (selectedMode === 'PNR Ticket Only') {
        // Generate a unique ticket number
        generateUniqueTicketNo().then(uniqueTicketNo => {
            ticketNoInput.value = uniqueTicketNo;
        });
    } else {
        // Clear the input field
        ticketNoInput.value = '';
    }
});

// Function to generate a unique ticket number
async function generateUniqueTicketNo() {
    let uniqueTicketNo = '';
    const response = await fetch('/generate_unique_ticket_no');
    const data = await response.json();
    if (data.success) {
        uniqueTicketNo = data.ticketNo;
    }
    return uniqueTicketNo;
}
// End: This function will generate a ticket number in the format "PNR-XXX-YYYYYY"




//Start: This function will validate the ticket number length
//ticket number is not less than 15 characters and display an error message 
document.addEventListener('DOMContentLoaded', function() {
    // Get the ticket number input element
    var ticketNoInput = document.getElementById('ticket_no');
    // Get the error message element
    var ticketNoError = document.getElementById('ticketNoError');

    // Add event listener to the form for form submission
    document.querySelector('form').addEventListener('submit', function(event) {
        // Validate ticket number length
        if (ticketNoInput.value.length >= 15) {
            // If ticket number length is valid, clear the error message
            ticketNoError.textContent = '';
        } else {
            // If ticket number length is invalid, display error message and prevent form submission
            ticketNoError.textContent = 'Ticket number must be at least 15 characters long.';
            event.preventDefault();
        }
    });
});
//End: This function will validate the ticket number length


