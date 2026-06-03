
function validateForm() {
    // Get the value of the select elements
    var selectedValueCustomer = document.getElementById('customer-ex-search').value;
    var selectedValueIncome = document.getElementById('income-ex-search-8').value;

    // Get the error message elements
    var clientCodeError = document.getElementById('clientCodeError');
    var incomeCodeError = document.getElementById('incomeCodeError');

    // Check if either of the values is empty
    if (selectedValueCustomer === '') {
        clientCodeError.textContent = 'Please select a Client Account.';
        return false;
    } else {
        // Clear any previous error messages
        clientCodeError.textContent = '';
    }

    if (selectedValueIncome === '') {
        incomeCodeError.textContent = 'Please select an Income Account.';
        return false;
    } else {
        // Clear any previous error messages
        incomeCodeError.textContent = '';
    }

    
    // Get the value of the input field
    var selectedValueAirlineExSearch1 = document.getElementById('airline-ex-search-1').value;
    var selectedValueAirlineExSearch2 = document.getElementById('airline-ex-search-2').value;
    var selectedValueAirlineExSearch3 = document.getElementById('airline-ex-search-3').value;
    var selectedValueAirlineExSearch4 = document.getElementById('airline-ex-search-4').value;
    var selectedValueAirlineExSearch5 = document.getElementById('airline-ex-search-5').value;
    var selectedValueAirlineExSearch6 = document.getElementById('airline-ex-search-6').value;
    var selectedValueAirlineExSearch7 = document.getElementById('airline-ex-search-7').value;

    // Get the value of the select elements
    var inputVisaApprovalPayableCR = document.getElementById('visa_approval_payable_cr').value;
    var inputAccommodation1PayableCR = document.getElementById('accommodation_1_payable_cr').value;
    var inputAccommodation2PayableCR = document.getElementById('accommodation_2_payable_cr').value;
    var inputTransportPayableCR = document.getElementById('transport_payable_cr').value;
    var inputZiaraatPayableCR = document.getElementById('ziaraat_payable_cr').value;
    var inputFoodPayableCR = document.getElementById('food_payable_cr').value;
    var inputOtherPayableCR = document.getElementById('other_payable_cr').value;

    // Get the error message elements
    var visa_approvalCodeError = document.getElementById('visa_approvalCodeError');
    var accommodation_1CodeError = document.getElementById('accommodation_1CodeError');
    var accommodation_2CodeError = document.getElementById('accommodation_2CodeError');
    var transportCodeError = document.getElementById('transportCodeError');
    var ziaraatCodeError = document.getElementById('ziaraatCodeError');
    var foodCodeError = document.getElementById('foodCodeError');
    var otherCodeError = document.getElementById('otherCodeError');

    // 1 Check if the input field is not empty and select element is empty for each select element
    if (inputVisaApprovalPayableCR !== null && inputVisaApprovalPayableCR !== undefined && inputVisaApprovalPayableCR !== '' && parseFloat(inputVisaApprovalPayableCR) !== 0 && selectedValueAirlineExSearch1 === '') {
        visa_approvalCodeError.textContent = 'Please select a Visa Approval Payable Account.';
        return false;
    } else {
        visa_approvalCodeError.textContent = '';
    }

    // 2 Check if the input field is not empty and select element is empty for each select element
    if (inputAccommodation1PayableCR !== null && inputAccommodation1PayableCR !== undefined && inputAccommodation1PayableCR !== '' && parseFloat(inputAccommodation1PayableCR) !== 0 && selectedValueAirlineExSearch2 === '') {
        accommodation_1CodeError.textContent = 'Please select an Accommodation 1 Payable Account.';
        return false;
    } else {
        accommodation_1CodeError.textContent = '';
    }

    // 3 Check if the input field is not empty and select element is empty for each select element
    if (inputAccommodation2PayableCR !== null && inputAccommodation2PayableCR !== undefined && inputAccommodation2PayableCR !== '' && parseFloat(inputAccommodation2PayableCR) !== 0 && selectedValueAirlineExSearch3 === '') {
        accommodation_2CodeError.textContent = 'Please select an Accommodation 2 Payable Account.';
        return false;
    } else {
        accommodation_2CodeError.textContent = '';
    }

    // 4 Check if the input field is not empty and select element is empty for each select element
    if (inputTransportPayableCR !== null && inputTransportPayableCR !== undefined && inputTransportPayableCR !== '' && parseFloat(inputTransportPayableCR) !== 0 && selectedValueAirlineExSearch4 === '') {
        transportCodeError.textContent = 'Please select a Transport Payable Account.';
        return false;
    } else {
        transportCodeError.textContent = '';
    }

    // 5 Check if the input field is not empty and select element is empty for each select element
    if (inputZiaraatPayableCR !== null && inputZiaraatPayableCR !== undefined && inputZiaraatPayableCR !== '' && parseFloat(inputZiaraatPayableCR) !== 0 && selectedValueAirlineExSearch5 === '') {
        ziaraatCodeError.textContent = 'Please select a Ziaraat Payable Account.';
        return false;
    } else {
        ziaraatCodeError.textContent = '';
    }

    // 6 Check if the input field is not empty and select element is empty for each select element
    if (inputFoodPayableCR !== null && inputFoodPayableCR !== undefined && inputFoodPayableCR !== '' && parseFloat(inputFoodPayableCR) !== 0 && selectedValueAirlineExSearch6 === '') {
        foodCodeError.textContent = 'Please select a Food Payable Account.';
        return false;
    } else {
        foodCodeError.textContent = '';
    }

    // 7 Check if the input field is not empty and select element is empty for each select element
    if (inputOtherPayableCR !== null && inputOtherPayableCR !== undefined && inputOtherPayableCR !== '' && parseFloat(inputOtherPayableCR) !== 0 && selectedValueAirlineExSearch7 === '') {
        otherCodeError.textContent = 'Please select an Other Payable Account.';
        return false;
    } else {
        otherCodeError.textContent = '';
    }

    // Allow the form to be submitted if all conditions are met
    return true;
}
