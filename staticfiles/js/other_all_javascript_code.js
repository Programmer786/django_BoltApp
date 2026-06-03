document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="text"][name$="_client_receivable"]');
    inputs.forEach(input => {
        input.addEventListener('input', calculateTotalClientReceivable);
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="text"][name$="_payable_cr"]');
    inputs.forEach(input => {
        input.addEventListener('input', calculateTotalPayable);
    });
});

function calculateTotalClientReceivable() {
    const visaApprovalClientReceivable = parseFloat(document.getElementById('visa_approval_client_receivable').value) || 0;
    const accommodation1ClientReceivable = parseFloat(document.getElementById('accommodation_1_client_receivable').value) || 0;
    const accommodation2ClientReceivable = parseFloat(document.getElementById('accommodation_2_client_receivable').value) || 0;
    const transportClientReceivable = parseFloat(document.getElementById('transport_client_receivable').value) || 0;
    const ziaraatClientReceivable = parseFloat(document.getElementById('ziaraat_client_receivable').value) || 0;
    const foodClientReceivable = parseFloat(document.getElementById('food_client_receivable').value) || 0;
    const otherClientReceivable = parseFloat(document.getElementById('other_client_receivable').value) || 0;

    const totalClientReceivable = visaApprovalClientReceivable + accommodation1ClientReceivable + accommodation2ClientReceivable + transportClientReceivable + ziaraatClientReceivable + foodClientReceivable + otherClientReceivable;

    document.getElementById('total_client_receivable').value = totalClientReceivable.toFixed(2);
    calculateTotalProfitLoss();
    calculateTotalGstPayable();
}

function calculateTotalPayable() {
    const visaApprovalPayableCR = parseFloat(document.getElementById('visa_approval_payable_cr').value) || 0;
    const accommodation1PayableCR = parseFloat(document.getElementById('accommodation_1_payable_cr').value) || 0;
    const accommodation2PayableCR = parseFloat(document.getElementById('accommodation_2_payable_cr').value) || 0;
    const transportPayableCR = parseFloat(document.getElementById('transport_payable_cr').value) || 0;
    const ziaraatPayableCR = parseFloat(document.getElementById('ziaraat_payable_cr').value) || 0;
    const foodPayableCR = parseFloat(document.getElementById('food_payable_cr').value) || 0;
    const otherPayableCR = parseFloat(document.getElementById('other_payable_cr').value) || 0;

    const totalPayableCR = visaApprovalPayableCR + accommodation1PayableCR + accommodation2PayableCR + transportPayableCR + ziaraatPayableCR + foodPayableCR + otherPayableCR;

    document.getElementById('total_payable_cr').value = totalPayableCR.toFixed(2);
    calculateTotalProfitLoss();
    calculateTotalGstPayable();
}


// Start: gst_payable_client_percent_calculate
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="text"][name$="gst_payable_client_percent"]');
    inputs.forEach(input => {
        input.addEventListener('input', calculateTotalGstPayable);
    });
});

function calculateTotalGstPayable() {
    const totalGSTPercent = parseFloat(document.getElementById('gst_payable_client_percent').value) || 0;
    const totalClientReceivable = parseFloat(document.getElementById('total_client_receivable').value) || 0;
    const totalPayableCR = parseFloat(document.getElementById('total_payable_cr').value) || 0;
    
    const totalGSTPercentCalculate = (totalClientReceivable-totalPayableCR) * (totalGSTPercent/100);

    document.getElementById('gst_payable_client_percent_calculate').value = totalGSTPercentCalculate.toFixed(2);

    calculateTotalProfitLoss();
}
// End: gst_payable_client_percent_calculate

function calculateTotalProfitLoss() {
    const totalClientReceivable = parseFloat(document.getElementById('total_client_receivable').value) || 0;
    const totalPayableCR = parseFloat(document.getElementById('total_payable_cr').value) || 0;
    
    const totalProfitLoss = totalClientReceivable - totalPayableCR;

    document.getElementById('profit_loss').value = totalProfitLoss.toFixed(2);
    document.getElementById('profit_show').value = totalProfitLoss.toFixed(2);

    // overall_total_client_receivable
    const totalGSTPercentCalculate = parseFloat(document.getElementById('gst_payable_client_percent_calculate').value) || 0;
    const overallTotalGSTPercentAndReceivableCalculate = totalClientReceivable + totalGSTPercentCalculate;
    document.getElementById('overall_total_client_receivable').value = overallTotalGSTPercentAndReceivableCalculate.toFixed(2);

    // overall_total_payable_breakup
    const getOverallTotalGSTPercentAndReceivableCalculate = parseFloat(document.getElementById('overall_total_client_receivable').value) || 0;
    const getTotalProfitLoss = parseFloat(document.getElementById('profit_loss').value) || 0;
    const overallTotalClientPayable = getOverallTotalGSTPercentAndReceivableCalculate - getTotalProfitLoss;
    document.getElementById('overall_total_payable_breakup').value = overallTotalClientPayable.toFixed(2);

}
