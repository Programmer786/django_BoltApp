// Function to handle form submission
document.getElementById('ledger-search-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent default form submission
    searchLedgerEntries(); // Call function to search ledger entries
});

// Function to search ledger entries
// Function to search ledger entries
function searchLedgerEntries() {
    // Get form data
    const formData = new FormData(document.getElementById('ledger-search-form'));
    const url = '/search_ledger_entries'; // URL to your backend route

    // Make AJAX request to backend
    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (Array.isArray(data.entries)) { // Check if data.entries is an array
            // Update table with search results
            updateTable(data.entries);
        } else {
            console.error('Invalid data format:', data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Function to update table with search results
function updateTable(entries) {
    const tableBody = document.getElementById('ledger-entries-body');
    tableBody.innerHTML = ''; // Clear table body

    // Iterate through search results and append rows to table
    entries.forEach(entry => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${entry.vtp}</td>
            <td>${formatDate(entry.invoice_date)}</td>
            <td>${entry.invoice_id}</td>
            <td>${entry.ticket_no}</td>
            <td>${entry.pnr}</td>
            <td>${entry.passport_no ? entry.passport_no : ''}</td>
            <td>${entry.description}</td>
            <td>${entry.debit !== 0 ? entry.debit : ''}</td>
            <td>${entry.credit !== 0 ? entry.credit : ''}</td>
            <td>${entry.balance}</td>
            <td>${entry.tp}</td>
            <td>${entry.ageing ? entry.ageing : ''}</td>
            <td>${entry.fare_taxes_breakup ? entry.fare_taxes_breakup : ''}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Function to format date in dd/mm/yyyy format
function formatDate(dateString) {
    const date = new Date(dateString);
    const day = date.getDate().toString().padStart(2, '0'); // Get day and pad with leading zero if needed
    const month = (date.getMonth() + 1).toString().padStart(2, '0'); // Get month (adding 1 because January is 0) and pad with leading zero if needed
    const year = date.getFullYear(); // Get full year

    return `${day}/${month}/${year}`; // Return formatted date string
}

//@app.route('/search_ledger_entries1', methods=['POST'])
//def search_ledger_entries1():
//    try:
//        # Retrieve search parameters from the request
//        account_code = request.form.get('account_code')
//        from_date = request.form.get('from_date')
//        to_date = request.form.get('to_date')
//
//        # Perform search query using the provided parameters
//        filtered_entries = Ledger.query.filter(Ledger.account_id == account_code, Ledger.isActive == 1, Ledger.invoice_date.between(from_date, to_date)).all()
//
//        # Serialize the filtered ledger entries to JSON
//        serialized_entries = []
//        for entry in filtered_entries:
//            serialized_entry = {
//                'vtp': entry.vtp,
//                'invoice_date': entry.invoice_date,
//                'invoice_id': entry.invoice_id,
//                'ticket_no': entry.ticket_no,
//                'pnr': entry.pnr,
//                'passport_no': entry.passport_no if entry.passport_no else '',
//                'description': entry.description,
//                'debit': entry.debit if entry.debit != 0 else '',
//                'credit': entry.credit if entry.credit != 0 else '',
//                'balance': entry.balance,
//                'tp': entry.tp,
//                'ageing': entry.ageing if entry.ageing else '',
//                'fare_taxes_breakup': entry.fare_taxes_breakup if entry.fare_taxes_breakup else ''
//            }
//            serialized_entries.append(serialized_entry)
//
//        # Return JSON response with filtered ledger entries
//        return jsonify({'entries': serialized_entries})  # Wrap the entries in a dictionary
//    except Exception as e:
//        return jsonify({'error': str(e)}), 500
