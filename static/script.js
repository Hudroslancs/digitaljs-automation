function calculateTotals() {

    let partsTotal = 0;

    const rowClasses = [
        "part-row-1",
        "part-row-2",
        "part-row-3",
        "part-row-4",
        "part-row-5",
        "part-row-6",
        "part-row-7",
        "part-row-8"
    ];

    rowClasses.forEach(rowClass => {

        const qtyField = document.querySelector(
            `.${rowClass}.qty`
        );

        const unitPriceField = document.querySelector(
            `.${rowClass}.unit-price`
        );

        const lineTotalField = document.querySelector(
            `.${rowClass}.line-total`
        );

        const qty = parseFloat(qtyField.value) || 0;
        const unitPrice = parseFloat(unitPriceField.value) || 0;

        const lineTotal = qty * unitPrice;

        lineTotalField.value = lineTotal.toFixed(2);

        partsTotal += lineTotal;
    });

    const serviceChargeField = document.querySelector(
        ".service-charge"
    );

    const serviceCharge =
        parseFloat(serviceChargeField?.value) || 0;

    const grandTotal = partsTotal + serviceCharge;

    const grandTotalField = document.querySelector(
        ".grand-total"
    );

    if (grandTotalField) {
        grandTotalField.value = grandTotal.toFixed(2);
    }
}

document.addEventListener("input", function (event) {

    if (
        event.target.classList.contains("qty") ||
        event.target.classList.contains("unit-price") ||
        event.target.classList.contains("service-charge")
    ) {
        calculateTotals();
    }

});
